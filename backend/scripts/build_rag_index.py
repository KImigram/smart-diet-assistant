"""Offline entry point: load -> clean -> split -> embed -> persist."""

import argparse
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rag.document_loader import load_recipe_documents
from rag.chunker import split_recipe_documents
from rag.embedder import create_embedder, get_model_path, model_signature
from rag.vector_store import build_index, get_index_path


def main():
    parser = argparse.ArgumentParser(description="使用本地 BGE-M3 在 CPU 上建立菜谱索引")
    parser.add_argument("--index", type=Path, default=get_index_path())
    parser.add_argument("--size", type=int, default=500)
    parser.add_argument("--overlap", type=int, default=80)
    args = parser.parse_args()
    if args.index.exists() and any(args.index.iterdir()):
        parser.error("索引目录非空，请用 --index 指定一个新的空目录")
    documents = load_recipe_documents()
    chunks = split_recipe_documents(documents, args.size, args.overlap)
    model_path = get_model_path()
    print(f"菜谱 {len(documents)} 篇，文本块 {len(chunks)} 个", flush=True)
    print(f"即将加载 CPU 模型：{model_path}", flush=True)
    signature = model_signature(model_path)
    embeddings = create_embedder(model_path)
    build_index(chunks, embeddings, args.index.resolve(), signature)
    print(f"建库完成：{args.index.resolve()}")


if __name__ == "__main__":
    main()
