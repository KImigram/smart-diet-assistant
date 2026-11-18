"""Benchmark correctness tests: no real model, cloud API or database required."""

import copy
import json
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / 'backend'))
from evals.benchmark import aggregate, compile_labels, load_cases, rank_metrics
from evals.compare_runs import compare
from evals import evaluate_retrieval as runner
from evals.sweep_thresholds import sweep
from rag.document_loader import load_recipe_documents
from rag.chunker import split_recipe_documents


def test_frozen_questions_match_real_corpus():
    cases = load_cases(PROJECT / 'backend/evals/rag_questions.jsonl')
    labels = compile_labels(cases, split_recipe_documents(load_recipe_documents()))
    assert len(cases) == 90
    assert sum(not c['answerable'] for c in cases) == 10
    assert all(labels[c['id']]['relevant'] for c in cases if c['answerable'])
    assert sum(c['category'] == 'multi_evidence' for c in cases) == 5


def test_metrics_do_not_confuse_same_document_with_evidence():
    label = {'relevant': {'a', 'b'}, 'groups': [{'a'}, {'b'}], 'sources': {'recipe.md'}}
    hits = [{'chunk_id':'wrong', 'source':'recipe.md'}, {'chunk_id':'a', 'source':'recipe.md'},
            {'chunk_id':'a', 'source':'recipe.md'}, {'chunk_id':'b', 'source':'recipe.md'}]
    metrics = rank_metrics(hits, label, [1, 2, 3])
    assert metrics['1']['document_hit'] == 1
    assert metrics['1']['evidence_hit'] == 0
    assert metrics['2']['evidence_recall'] == .5
    assert metrics['2']['all_evidence_hit'] == 0
    assert metrics['2']['evidence_precision'] == .5
    assert metrics['2']['mrr'] == .5
    assert metrics['3']['evidence_group_coverage'] == 1
    assert metrics['3']['all_evidence_hit'] == 1
    assert 0 < metrics['3']['ndcg'] < 1


def test_precision_uses_fixed_k_when_fewer_results():
    label = {'relevant': {'a'}, 'groups': [{'a'}], 'sources': {'s'}}
    assert rank_metrics([{'chunk_id':'a','source':'s'}], label, [5])['5']['evidence_precision'] == .2


def test_missing_evidence_is_not_silently_skipped():
    case = {'id':'x', 'evidence':[{'source':'none','section':'操作','quote':'不在语料中'}]}
    with pytest.raises(ValueError, match='无法匹配'):
        compile_labels([case], [])


def test_equivalent_evidence_forms_one_required_group():
    from langchain_core.documents import Document
    chunks = [Document(page_content='蒜蓉酱',metadata={'local_path':'a','section':s,'chunk_id':s})
              for s in ['原料','计算']]
    case = {'id':'x','evidence':[{'source':'a','section':'原料','quote':'蒜蓉酱',
                                'alternatives':[{'section':'计算','quote':'蒜蓉酱'}]}]}
    label = compile_labels([case], chunks)['x']
    assert len(label['groups']) == 1
    assert label['relevant'] == {'原料','计算'}
    metrics = rank_metrics([{'chunk_id':'计算','source':'a'}], label, [1])['1']
    assert metrics['evidence_group_coverage'] == 1
    assert metrics['evidence_recall'] == .5


def test_v2_changes_only_dev_evidence():
    original = load_cases(PROJECT/'backend/evals/rag_questions.jsonl')
    revised = load_cases(PROJECT/'backend/evals/rag_questions_v2.jsonl')
    changed = []
    for left, right in zip(original, revised):
        if left != right:
            changed.append(left['id'])
            assert left['split'] == 'dev'
            assert {k:v for k,v in left.items() if k != 'evidence'} == {k:v for k,v in right.items() if k != 'evidence'}
            assert left['evidence'] == [{k:v for k,v in e.items() if k != 'alternatives'} for e in right['evidence']]
    assert len(changed) == 11
    compile_labels(revised, split_recipe_documents(load_recipe_documents()))


def test_expanded_questions_preserve_regression_and_cover_new_scenarios():
    original = load_cases(PROJECT/'backend/evals/rag_questions_v2.jsonl')
    expanded = load_cases(PROJECT/'backend/evals/rag_questions_v3.jsonl')
    assert expanded[:len(original)] == original
    assert len(expanded) == 200
    assert sum(not c['answerable'] for c in expanded) == 30
    sources = {e['source'] for c in expanded for e in c['evidence']}
    assert len(sources) == 60
    added = expanded[len(original):]
    assert len([c for c in added if c['category'] == 'long_history_followup']) == 10
    assert all(len(c['history']) == 8 for c in added if c['category'] == 'long_history_followup')
    assert {c.get('negative_kind') for c in added if not c['answerable']} == {
        'missing_recipe', 'unsupported_nutrition', 'requires_database',
        'out_of_domain', 'unsupported_medical', 'missing_detail'}
    compile_labels(expanded, split_recipe_documents(load_recipe_documents()))


def test_history_distractors_cannot_leak_across_splits(tmp_path):
    cases = [{'id':split, 'split':split, 'question':'question', 'history':[],
              'answerable':False, 'evidence':[], 'related_sources':['same.md']}
             for split in ['dev','test']]
    path = tmp_path/'invalid.jsonl'
    path.write_text('\n'.join(json.dumps(c) for c in cases), encoding='utf-8')
    with pytest.raises(ValueError, match='跨 dev/test'):
        load_cases(path)


def test_multifact_suite_really_requires_multiple_chunks():
    cases = load_cases(PROJECT/'backend/evals/rag_multifact_v1.jsonl')
    labels = compile_labels(cases, split_recipe_documents(load_recipe_documents()))
    assert len(cases) >= 30
    assert {c['category'] for c in cases} == {'cross_recipe_multifact', 'same_recipe_multifact', 'three_fact'}
    for case in cases:
        label = labels[case['id']]
        assert len(label['groups']) >= 2
        assert not set.intersection(*label['groups'])
        hits = [{'chunk_id':identity, 'source':'ignored'} for identity in sorted(label['relevant'])]
        metrics = rank_metrics(hits, label, [1, len(hits)])
        assert metrics['1']['all_evidence_hit'] == 0
        assert metrics[str(len(hits))]['all_evidence_hit'] == 1


def test_errors_are_not_counted_as_successful_negative_rejections():
    rows = [{'answerable':False,'error':'boom','accepted':[]},
            {'answerable':False,'error':None,'accepted':[]}]
    summary = aggregate(rows, [1])
    assert summary['negative_rejection_rate'] == .5
    assert summary['errors'] == 1


def test_runner_writes_complete_report_without_model(tmp_path, monkeypatch):
    from evals import adapters
    chunk = split_recipe_documents(load_recipe_documents())[0]

    class FakeAdapter:
        info = {'name':'test-only'}
        def retrieve(self, question, history, k):
            return [{'chunk_id':chunk.metadata['chunk_id'], 'source':chunk.metadata['local_path'],
                     'content':chunk.page_content, 'score':0.2, 'accepted':True}]

    monkeypatch.setattr(adapters, 'create_dense', lambda options: FakeAdapter())
    out = tmp_path / 'report'
    monkeypatch.setattr(sys, 'argv', ['eval', '--output', str(out), '--split','dev'])
    runner.main()
    report = json.loads((out/'report.json').read_text(encoding='utf-8'))
    assert report['summary']['errors'] == 0
    assert report['summary']['questions'] == len(report['rows'])
    assert (out/'summary.md').exists()
    assert report['summary']['negative_rejection_rate'] == 0
    assert report['by_cohort']['regression']['questions'] == 46
    assert report['by_cohort']['new']['questions'] > 0
    assert report['by_category']['history_correction']['questions'] > 0
    assert report['by_negative_kind']['requires_database']['questions'] > 0
    report['adapter_info']['score_type'] = 'cosine_distance_lower_is_better'
    results = sweep(report, [.1, .3], 3)
    assert len(results[1]['positive_empty_ids']) == report['summary']['answerable']
    assert results[1]['summary']['negative_rejection_rate'] == 1
    assert results[2]['summary']['negative_rejection_rate'] == 0
    assert 'delta=+0.0000' in compare(report, copy.deepcopy(report))
    changed = copy.deepcopy(report)
    changed['dataset_hash'] = 'different'
    with pytest.raises(ValueError, match='dataset_hash'):
        compare(report, changed)


def test_regression_suite_uses_only_original_dev_cases(tmp_path, monkeypatch):
    from evals import adapters
    class EmptyAdapter:
        info = {'name':'test-only'}
        def retrieve(self, question, history, k):
            return []
    monkeypatch.setattr(adapters, 'create_dense', lambda options: EmptyAdapter())
    out = tmp_path/'regression'
    monkeypatch.setattr(sys, 'argv', ['eval', '--suite', 'regression', '--output', str(out)])
    runner.main()
    report = json.loads((out/'report.json').read_text(encoding='utf-8'))
    assert report['summary']['questions'] == 46
    assert list(report['by_cohort']) == ['regression']
    assert report['case_ids'] == [c['id'] for c in load_cases(PROJECT/'backend/evals/rag_questions_v2.jsonl') if c['split']=='dev']


def test_category_and_cohort_filters_select_only_requested_cases(tmp_path, monkeypatch):
    from evals import adapters
    class EmptyAdapter:
        info = {'name':'test-only'}
        def retrieve(self, question, history, k):
            return []
    monkeypatch.setattr(adapters, 'create_dense', lambda options: EmptyAdapter())
    out = tmp_path/'filtered'
    monkeypatch.setattr(sys, 'argv', ['eval', '--suite','expanded', '--cohort','new',
                                     '--category','long_history_followup', '--output',str(out)])
    runner.main()
    report = json.loads((out/'report.json').read_text(encoding='utf-8'))
    assert report['summary']['questions'] > 0
    assert all(row['cohort']=='new' and row['category']=='long_history_followup' for row in report['rows'])
