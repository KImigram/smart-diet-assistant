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
    assert metrics['2']['evidence_precision'] == .5
    assert metrics['2']['mrr'] == .5
    assert metrics['3']['evidence_group_coverage'] == 1
    assert 0 < metrics['3']['ndcg'] < 1


def test_precision_uses_fixed_k_when_fewer_results():
    label = {'relevant': {'a'}, 'groups': [{'a'}], 'sources': {'s'}}
    assert rank_metrics([{'chunk_id':'a','source':'s'}], label, [5])['5']['evidence_precision'] == .2


def test_missing_evidence_is_not_silently_skipped():
    case = {'id':'x', 'evidence':[{'source':'none','section':'操作','quote':'不在语料中'}]}
    with pytest.raises(ValueError, match='无法匹配'):
        compile_labels([case], [])


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
    assert 'delta=+0.0000' in compare(report, copy.deepcopy(report))
    changed = copy.deepcopy(report)
    changed['dataset_hash'] = 'different'
    with pytest.raises(ValueError, match='dataset_hash'):
        compare(report, changed)
