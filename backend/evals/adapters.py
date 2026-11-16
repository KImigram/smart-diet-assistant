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


class RewriteDenseAdapter(DenseAdapter):
    def __init__(self, options: dict):
        from rag.query_rewriter import create_rewrite_model
        self.rewrite_model = create_rewrite_model()
        super().__init__(options)
        from config import LLM_MODEL
        self.info.update(name="rewrite+dense-bge-m3", rewrite_model=LLM_MODEL,
                         rewrite_temperature=0, rewrite_history_messages=12,
                         rewrite_history_character_budget=8000)

    def retrieve(self, question: str, history: list[dict], k: int) -> list[dict]:
        from rag.query_rewriter import rewrite_question
        self.last_rewrite = rewrite_question(question, history, self.rewrite_model)
        return super().retrieve(self.last_rewrite['query'], [], k)


def create_rewrite_dense(options: dict):
    return RewriteDenseAdapter(options)
