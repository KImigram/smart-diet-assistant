"""Lazy, process-local BGE-M3/Chroma runtime shared by chat requests."""

import os
from threading import Lock

from rag.embedder import create_embedder, get_model_path, model_signature
from rag.retriever import retrieve
from rag.vector_store import get_index_path, open_index, validate_index
from rag.hybrid_retriever import BM25Index, hybrid_retrieve

_store = None
_lexical = None
_lock = Lock()


def recipe_context(question: str) -> list[dict]:
    global _store, _lexical
    k = int(os.getenv("RAG_TOP_K") or "3")
    threshold = os.getenv("RAG_MAX_DISTANCE", "").strip()
    max_distance = float(threshold) if threshold else None
    mode = os.getenv('RAG_RETRIEVAL_MODE', 'dense').strip().lower()
    if mode not in {'dense', 'bm25', 'hybrid'}:
        raise ValueError('RAG_RETRIEVAL_MODE 必须是 dense、bm25 或 hybrid')
    if mode != 'dense' and max_distance is not None:
        raise ValueError('BM25/RRF 分数不能使用 RAG_MAX_DISTANCE，请留空')
    if k < 1 or (max_distance is not None and not 0 <= max_distance <= 2):
        raise ValueError("RAG_TOP_K 必须大于 0；RAG_MAX_DISTANCE 须在 0 到 2 之间")
    # Serialize first initialization and CPU inference to bound concurrent memory use.
    with _lock:
        if mode != 'bm25' and _store is None:
            path = get_model_path()
            signature = model_signature(path)
            index = get_index_path()
            validate_index(index, signature)
            _store = open_index(create_embedder(path), index, signature)
            # If BM25 was previously used alone, rebuild from the exact saved corpus.
            _lexical = None
        if mode != 'dense' and _lexical is None:
            if _store is not None:
                _lexical = BM25Index.from_store(_store)
            else:
                from rag.document_loader import load_recipe_documents
                from rag.chunker import split_recipe_documents
                _lexical = BM25Index(split_recipe_documents(load_recipe_documents()))
        if mode == 'hybrid':
            hits = hybrid_retrieve(_store, _lexical, question, k,
                                   int(os.getenv('RAG_CANDIDATE_K', '20')),
                                   int(os.getenv('RAG_RRF_CONSTANT', '60')))
        elif mode == 'bm25':
            hits = _lexical.search(question, k)
        else:
            hits = retrieve(_store, question, k, max_distance)
    return [
        {"citation": f"R{i}", "title": doc.metadata["title"],
         "section": doc.metadata["section"], "source": doc.metadata["source"],
         "chunk_id": doc.metadata["chunk_id"], "distance": score if mode == 'dense' else None,
         "retrieval_score": score, "retrieval_mode": mode,
         "content": doc.page_content}
        for i, (doc, score) in enumerate(hits, 1)
    ]
