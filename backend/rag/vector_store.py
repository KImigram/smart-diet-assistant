"""Persist a new Chroma index and validate its embedding configuration on open."""

import json
import os
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

DEFAULT_INDEX_DIR = Path(__file__).resolve().parents[1] / "data" / "vector_db" / "bge_m3_v1"
COLLECTION = "recipe_chunks"


def get_index_path() -> Path:
    return Path(os.getenv("RAG_INDEX_PATH") or DEFAULT_INDEX_DIR).resolve()


def build_index(chunks: list[Document], embeddings: Embeddings, index_path: Path, signature: str) -> Chroma:
    if not chunks:
        raise ValueError("不能用空文本块列表建库")
    if index_path.exists() and any(index_path.iterdir()):
        raise FileExistsError(f"索引目录非空，请用 --index 指定新目录：{index_path}")
    ids = [chunk.metadata["chunk_id"] for chunk in chunks]
    if len(set(ids)) != len(ids):
        raise ValueError("存在重复的 chunk_id")
    index_path.mkdir(parents=True, exist_ok=True)
    store = Chroma(
        collection_name=COLLECTION,
        persist_directory=str(index_path),
        embedding_function=embeddings,
        collection_metadata={"hnsw:space": "cosine"},
    )
    # Small batches limit CPU embedding memory usage.
    for offset in range(0, len(chunks), 16):
        batch = chunks[offset:offset + 16]
        store.add_documents(batch, ids=ids[offset:offset + 16])
        print(f"已入库 {min(offset + 16, len(chunks))}/{len(chunks)}", flush=True)
    manifest = {
        "schema_version": 1,
        "collection": COLLECTION,
        "embedding_signature": signature,
        "normalize_embeddings": True,
        "distance": "cosine",
        "chunk_count": len(chunks),
        "chunk_sizes": sorted({c.metadata["chunk_size"] for c in chunks}),
        "chunk_overlaps": sorted({c.metadata["chunk_overlap"] for c in chunks}),
    }
    # Only a fully built index gets a manifest. Incomplete builds cannot be opened.
    (index_path / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return store


def validate_index(index_path: Path, signature: str) -> dict:
    manifest = json.loads((index_path / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("embedding_signature") != signature:
        raise ValueError("模型文件或配置已改变，需要使用原模型或重新建库")
    if (manifest.get("schema_version"), manifest.get("collection"), manifest.get("distance"),
            manifest.get("normalize_embeddings")) != (1, COLLECTION, "cosine", True):
        raise ValueError("索引配置不兼容，请重新建库")
    return manifest


def open_index(embeddings: Embeddings, index_path: Path, signature: str) -> Chroma:
    validate_index(index_path, signature)
    return Chroma(
        collection_name=COLLECTION,
        persist_directory=str(index_path),
        embedding_function=embeddings,
        create_collection_if_not_exists=False,
    )
