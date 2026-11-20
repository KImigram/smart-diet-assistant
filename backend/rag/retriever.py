"""Return relevant chunks with cosine distances, sources and optional filtering."""

from langchain_chroma import Chroma
from langchain_core.documents import Document


def retrieve(
    store: Chroma,
    question: str,
    k: int = 3,
    max_distance: float | None = None,
) -> list[tuple[Document, float]]:
    if not question.strip():
        raise ValueError("问题不能为空")
    if k < 1 or (max_distance is not None and not 0 <= max_distance <= 2):
        raise ValueError("要求 k >= 1，余弦距离阈值在 0 到 2 之间")
    results = store.similarity_search_with_score(question, k=k)
    selected = []
    seen = set()
    for document, distance in results:
        if max_distance is not None and distance > max_distance:
            continue
        identity = document.metadata["chunk_id"]
        if identity not in seen:
            selected.append((document, float(distance)))
            seen.add(identity)
    return selected
