"""Adapter interface: retrieve(question, history, k) -> candidate dictionaries.

Each dictionary has chunk_id, source (local_path), content, score and accepted.
Adapters must return candidates in rank order. Scores are diagnostic only:
BM25, cosine distances and reranker scores must not share a universal threshold.
"""

from rag.embedder import create_embedder, get_model_path, model_signature
from rag.vector_store import get_index_path, open_index, validate_index
from rag.retriever import retrieve


class DenseAdapter:
    def __init__(self, options: dict):
        from pathlib import Path
        path = get_model_path()
        index = Path(options.get("index") or get_index_path()).resolve()
        signature = model_signature(path)
        self.manifest = validate_index(index, signature)
        self.max_distance = options.get("max_distance")
        if self.max_distance is not None and not 0 <= self.max_distance <= 2:
            raise ValueError("max_distance 必须在 0 到 2 之间")
        self.store = open_index(create_embedder(path), index, signature)
        self.info = {"name": "dense-bge-m3", "index": str(index),
                     "manifest": self.manifest, "options": options,
                     "score_type": "cosine_distance_lower_is_better"}

    def retrieve(self, question: str, history: list[dict], k: int) -> list[dict]:
        # Baseline intentionally ignores history; future rewriting adapters use it.
        return [
            {"chunk_id": doc.metadata["chunk_id"], "source": doc.metadata["local_path"],
             "title": doc.metadata["title"], "section": doc.metadata["section"],
             "content": doc.page_content, "score": float(distance),
             "accepted": self.max_distance is None or distance <= self.max_distance}
            for doc, distance in retrieve(self.store, question, k=k)
        ]


def create_dense(options: dict):
    return DenseAdapter(options)


class RewriteMixin:
    def _init_rewrite(self, options: dict):
        import json
        from pathlib import Path
        from rag.query_rewriter import create_rewrite_model
        self.rewrite_model = create_rewrite_model()
        self.cache_path = Path(options['rewrite_cache']) if options.get('rewrite_cache') else None
        self.query_cache = json.loads(self.cache_path.read_text(encoding='utf-8')) if self.cache_path and self.cache_path.exists() else {}
        from config import LLM_MODEL
        self.info.update(name="rewrite+" + self.info['name'], rewrite_model=LLM_MODEL,
                         rewrite_temperature=0, rewrite_history_messages=12,
                         rewrite_history_character_budget=8000,
                         rewrite_cache=str(self.cache_path) if self.cache_path else None)

    def retrieve(self, question: str, history: list[dict], k: int) -> list[dict]:
        import json
        from evals.benchmark import digest
        from rag.query_rewriter import rewrite_question
        # Shared cache contains only question/history/model -> rewrite, never evidence.
        key = digest({'question': question, 'history': history, 'model': self.info['rewrite_model']})
        cached = self.query_cache.get(key)
        if cached is not None:
            self.last_rewrite = dict(cached, elapsed_ms=0, cache_hit=True)
        else:
            self.last_rewrite = dict(rewrite_question(question, history, self.rewrite_model), cache_hit=False)
            if self.cache_path and self.last_rewrite['status'] != 'fallback':
                self.query_cache[key] = self.last_rewrite
                self.cache_path.parent.mkdir(parents=True, exist_ok=True)
                self.cache_path.write_text(json.dumps(self.query_cache, ensure_ascii=False, indent=2), encoding='utf-8')
        return super().retrieve(self.last_rewrite['query'], [], k)


class RewriteDenseAdapter(RewriteMixin, DenseAdapter):
    def __init__(self, options: dict):
        DenseAdapter.__init__(self, options)
        self._init_rewrite(options)


def create_rewrite_dense(options: dict):
    return RewriteDenseAdapter(options)


class BM25Adapter:
    def __init__(self, options: dict):
        from rag.chunker import split_recipe_documents
        from rag.document_loader import load_recipe_documents
        from rag.hybrid_retriever import BM25Index
        if options.get('max_distance') is not None:
            raise ValueError('BM25 分数不能使用余弦距离阈值')
        self.lexical = BM25Index(split_recipe_documents(load_recipe_documents(),
                                int(options.get('size', 500)), int(options.get('overlap', 80))))
        self.info = {'name':'bm25-jieba', 'score_type':'bm25_higher_is_better',
                     'tokenizer':'jieba-0.42.1/HMM=False', 'k1':1.5, 'b':0.75,
                     'chunk_count':len(self.lexical.chunks), 'options':options}

    def retrieve(self, question: str, history: list[dict], k: int) -> list[dict]:
        return _scored_hits(self.lexical.search(question, k))


def _scored_hits(hits):
    return [{'chunk_id':doc.metadata['chunk_id'], 'source':doc.metadata['local_path'],
             'title':doc.metadata['title'], 'section':doc.metadata['section'],
             'content':doc.page_content, 'score':float(score), 'accepted':True}
            for doc, score in hits]


class HybridAdapter(DenseAdapter):
    def __init__(self, options: dict):
        from rag.hybrid_retriever import BM25Index
        if options.get('max_distance') is not None:
            raise ValueError('RRF 融合分数不能使用余弦距离阈值')
        super().__init__(options)
        self.lexical = BM25Index.from_store(self.store)
        self.candidate_k = int(options.get('candidate_k', 20))
        self.rrf_constant = int(options.get('rrf_constant', 60))
        self.info.update(name='hybrid-bge-m3-bm25', score_type='rrf_higher_is_better',
                         candidate_k=self.candidate_k, rrf_constant=self.rrf_constant,
                         tokenizer='jieba-0.42.1/HMM=False', branch_weights=[1, 1])

    def retrieve(self, question: str, history: list[dict], k: int) -> list[dict]:
        from rag.hybrid_retriever import hybrid_retrieve
        return _scored_hits(hybrid_retrieve(self.store, self.lexical, question, k,
                                           self.candidate_k, self.rrf_constant))


class RewriteBM25Adapter(RewriteMixin, BM25Adapter):
    def __init__(self, options: dict):
        BM25Adapter.__init__(self, options)
        self._init_rewrite(options)


class RewriteHybridAdapter(RewriteMixin, HybridAdapter):
    def __init__(self, options: dict):
        HybridAdapter.__init__(self, options)
        self._init_rewrite(options)


def create_bm25(options: dict):
    return BM25Adapter(options)


def create_hybrid(options: dict):
    return HybridAdapter(options)


def create_rewrite_bm25(options: dict):
    return RewriteBM25Adapter(options)


def create_rewrite_hybrid(options: dict):
    return RewriteHybridAdapter(options)
