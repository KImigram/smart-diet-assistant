"""Chinese BM25 and reciprocal rank fusion over the existing recipe chunks."""
# bm25进行关键词排序 
import logging
import math
import re

import jieba
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from rag.retriever import retrieve

TOKEN_PATTERN = re.compile(r"[\u4e00-\u9fffA-Za-z0-9]+")


def tokenize(text: str) -> list[str]:
    # The same tokenizer is used for corpus and query; no question-specific words.
    return [word for word in jieba.lcut(text.lower(), HMM=False)
            if TOKEN_PATTERN.fullmatch(word)]


class BM25Index:
    def __init__(self, chunks: list[Document]):
        if not chunks:
            raise ValueError("BM25 语料不能为空")
        self.chunks = sorted(chunks, key=lambda doc: doc.metadata["chunk_id"])
        ids = [doc.metadata["chunk_id"] for doc in self.chunks]
        if len(set(ids)) != len(ids):
            raise ValueError("BM25 存在重复的 chunk_id")
        jieba.setLogLevel(logging.WARNING)
        tokens = [tokenize(doc.page_content) for doc in self.chunks]
        if not any(tokens):
            raise ValueError("BM25 语料分词结果为空")
        self.model = BM25Okapi(tokens, k1=1.5, b=0.75, epsilon=0.25)

    @classmethod
    def from_store(cls, store):
        saved = store.get(include=["documents", "metadatas"])
        return cls([Document(page_content=text, metadata=metadata)
                    for text, metadata in zip(saved["documents"], saved["metadatas"])])

    def search(self, question: str, k: int) -> list[tuple[Document, float]]:
        if not question.strip() or k < 1:
            raise ValueError("问题不能为空，k 必须大于 0")
        tokens = tokenize(question)
        if not tokens:
            return []
        scores = self.model.get_scores(tokens)
        # Zero score means no useful lexical match; do not pad with arbitrary chunks.
        ranked = sorted((i for i, score in enumerate(scores) if score > 0),
                        key=lambda i: (-float(scores[i]), self.chunks[i].metadata["chunk_id"]))
        return [(self.chunks[i], float(scores[i])) for i in ranked[:k]]


def reciprocal_rank_fusion(rankings, k: int, rrf_constant: int = 60):
    """Each distinct chunk contributes once per branch: sum(1 / (c + rank))."""
    if k < 1 or rrf_constant < 1:
        raise ValueError("k 和 RRF 常数必须大于 0")
    documents, scores = {}, {}
    for ranking in rankings:
        seen = set()
        for doc, _ in ranking:
            identity = doc.metadata["chunk_id"]
            if identity in seen:
                continue
            seen.add(identity)
            rank = len(seen)
            documents[identity] = doc
            scores[identity] = scores.get(identity, 0.0) + 1 / (rrf_constant + rank)
    ordered = sorted(scores, key=lambda identity: (-scores[identity], identity))
    return [(documents[identity], scores[identity]) for identity in ordered[:k]]


def hybrid_retrieve(store, lexical: BM25Index, question: str, k: int = 3,
                    candidate_k: int = 20, rrf_constant: int = 60):
    if candidate_k < k:
        raise ValueError("每路候选数量必须不小于最终 k")
    if not math.isfinite(rrf_constant) or rrf_constant < 1:
        raise ValueError("RRF 常数必须大于 0")
    dense = retrieve(store, question, k=candidate_k)
    sparse = lexical.search(question, candidate_k)
    return reciprocal_rank_fusion([dense, sparse], k, rrf_constant)
