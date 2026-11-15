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
