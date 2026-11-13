"""Lazy, process-local BGE-M3/Chroma runtime shared by chat requests."""

import os
from threading import Lock

from rag.embedder import create_embedder, get_model_path, model_signature
from rag.retriever import retrieve
from rag.vector_store import get_index_path, open_index, validate_index

_store = None
_lock = Lock()


def recipe_context(question: str) -> list[dict]:
    global _store
    k = int(os.getenv("RAG_TOP_K") or "3")
    threshold = os.getenv("RAG_MAX_DISTANCE", "").strip()
    max_distance = float(threshold) if threshold else None
    if k < 1 or (max_distance is not None and not 0 <= max_distance <= 2):
        raise ValueError("RAG_TOP_K 必须大于 0；RAG_MAX_DISTANCE 须在 0 到 2 之间")
    # Serialize first initialization and CPU inference to bound concurrent memory use.
    with _lock:
        if _store is None:
            path = get_model_path()
            signature = model_signature(path)
            index = get_index_path()
            validate_index(index, signature)
            _store = open_index(create_embedder(path), index, signature)
        hits = retrieve(_store, question, k, max_distance)
    return [
        {"citation": f"R{i}", "title": doc.metadata["title"],
         "section": doc.metadata["section"], "source": doc.metadata["source"],
         "chunk_id": doc.metadata["chunk_id"], "distance": distance,
         "content": doc.page_content}
        for i, (doc, distance) in enumerate(hits, 1)
    ]
