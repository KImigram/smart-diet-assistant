"""Test Chroma persistence and retrieval using tiny hand-written vectors."""

import sys
from pathlib import Path

import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from rag.vector_store import build_index, open_index, validate_index
from rag.retriever import retrieve


class ExampleEmbeddings(Embeddings):
    """No trained model, downloads, GPU or external services."""

    def embed_documents(self, texts):
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text):
        return [1.0, 0.0] if "鸡" in text else [0.0, 1.0]


def test_persist_reopen_retrieve_and_threshold(tmp_path):
    chunks = [
        Document(page_content="鸡肉的做法", metadata={"chunk_id": "chicken", "source": "a", "chunk_size": 500, "chunk_overlap": 80}),
        Document(page_content="黄瓜的做法", metadata={"chunk_id": "cucumber", "source": "b", "chunk_size": 500, "chunk_overlap": 80}),
    ]
    path = tmp_path / "index"
    embeddings = ExampleEmbeddings()
    build_index(chunks, embeddings, path, "test-signature")
    store = open_index(embeddings, path, "test-signature")
    hits = retrieve(store, "鸡肉怎么做", k=2, max_distance=0.1)
    assert len(hits) == 1
    assert hits[0][0].metadata["source"] == "a"
    assert hits[0][1] == pytest.approx(0.0, abs=1e-6)
    with pytest.raises(ValueError, match="模型文件"):
        validate_index(path, "different-model")
    with pytest.raises(FileExistsError):
        build_index(chunks, embeddings, path, "test-signature")


def test_missing_index_does_not_create_directory(tmp_path):
    path = tmp_path / "missing"
    with pytest.raises(FileNotFoundError):
        open_index(ExampleEmbeddings(), path, "test")
    assert not path.exists()
