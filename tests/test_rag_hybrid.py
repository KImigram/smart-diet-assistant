"""Keyword retrieval and fusion tests without local weights or cloud requests."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from langchain_core.documents import Document

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from rag.hybrid_retriever import BM25Index, tokenize, reciprocal_rank_fusion, hybrid_retrieve
from rag import runtime
from evals import adapters


def doc(identity, text):
    return Document(page_content=text, metadata={'chunk_id':identity, 'title':text,
                    'section':'食材', 'source':'https://example.org/' + identity,
                    'local_path':identity + '.md'})


def test_chinese_bm25_matches_rare_ingredient_and_returns_no_arbitrary_matches():
    chunks = [doc('a', '蒜蓉虾需要大蒜和鲜虾'), doc('b', '蛋挞需要牛奶和淡奶油'),
              doc('c', '番茄鸡蛋面需要面条'), doc('d', '黄瓜凉拌加醋')]
    index = BM25Index(chunks)
    assert '奶油' in tokenize('淡奶油，需要多少？')
    assert index.search('淡奶油', 3)[0][0].metadata['chunk_id'] == 'b'
    assert index.search('量子纠缠', 3) == []
    assert index.search('？！', 3) == []


def test_rrf_uses_ranks_deduplicates_and_breaks_ties_stably():
    a, b, c = [doc(x, x) for x in 'abc']
    fused = reciprocal_rank_fusion([[(a, 999), (a, 1), (b, .01)],
                                     [(b, 999999), (c, .001)]], 3)
    assert [d.metadata['chunk_id'] for d, _ in fused] == ['b', 'a', 'c']
    assert fused[0][1] == pytest.approx(1/62 + 1/61)
    assert fused[1][1] == pytest.approx(1/61)
    tied = reciprocal_rank_fusion([[(b, 0)], [(a, 0)]], 2)
    assert [d.metadata['chunk_id'] for d, _ in tied] == ['a', 'b']


def test_hybrid_uses_candidate_pool_before_final_k():
    a, b = doc('a', 'a'), doc('b', 'b')
    calls = []
    store = SimpleNamespace(similarity_search_with_score=lambda query, k:
                            (calls.append(k) or [(a, .1), (b, .2)]))
    lexical = SimpleNamespace(search=lambda query, k: [(b, 5)])
    assert hybrid_retrieve(store, lexical, '问题', 1, 2)[0][0].metadata['chunk_id'] == 'b'
    assert calls == [2]
    with pytest.raises(ValueError):
        hybrid_retrieve(store, lexical, '问题', 3, 2)


def test_hybrid_cannot_apply_cosine_threshold(monkeypatch):
    monkeypatch.setenv('RAG_RETRIEVAL_MODE', 'hybrid')
    monkeypatch.setenv('RAG_MAX_DISTANCE', '.4')
    monkeypatch.setattr(runtime, 'create_embedder', lambda *a: pytest.fail('must not load'))
    with pytest.raises(ValueError, match='RAG_MAX_DISTANCE'):
        runtime.recipe_context('蒜蓉虾')
    with pytest.raises(ValueError, match='余弦距离'):
        adapters.HybridAdapter({'max_distance':.4})


def test_bm25_runtime_does_not_load_embeddings(monkeypatch):
    monkeypatch.setenv('RAG_RETRIEVAL_MODE', 'bm25')
    monkeypatch.setenv('RAG_MAX_DISTANCE', '')
    monkeypatch.setattr(runtime, '_store', None)
    monkeypatch.setattr(runtime, '_lexical', SimpleNamespace(search=lambda q, k: [(doc('a','虾'), 2.5)]))
    monkeypatch.setattr(runtime, 'create_embedder', lambda *a: pytest.fail('must not load'))
    hit = runtime.recipe_context('虾')[0]
    assert hit['distance'] is None and hit['retrieval_score'] == 2.5
    assert hit['citation'] == 'R1'


def test_shared_rewrite_cache_reuses_query_without_evidence(tmp_path, monkeypatch):
    from rag import query_rewriter
    calls = []
    monkeypatch.setattr(query_rewriter, 'create_rewrite_model', lambda: object())
    def rewrite(question, history, model):
        calls.append(question)
        return {'original':question, 'query':'蒜蓉虾蒸多久', 'changed':True,
                'status':'ok', 'error':None, 'elapsed_ms':100}
    monkeypatch.setattr(query_rewriter, 'rewrite_question', rewrite)

    class Base:
        def retrieve(self, question, history, k):
            return question
    class Example(adapters.RewriteMixin, Base):
        def __init__(self):
            self.info = {'name':'fake'}
            self._init_rewrite({'rewrite_cache':str(tmp_path/'queries.json')})
    history = [{'role':'user', 'content':'蒜蓉虾怎么做'}]
    first, second = Example(), None
    assert first.retrieve('蒸多久', history, 3) == '蒜蓉虾蒸多久'
    second = Example()
    assert second.retrieve('蒸多久', history, 3) == '蒜蓉虾蒸多久'
    assert second.last_rewrite['cache_hit'] and calls == ['蒸多久']
    second.retrieve('需要什么材料', history, 3)
    assert len(calls) == 2
