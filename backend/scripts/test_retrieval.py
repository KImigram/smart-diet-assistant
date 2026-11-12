"""Manual retrieval inspection; this is not a pytest test or answer generator."""

import argparse
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rag.embedder import create_embedder, get_model_path, model_signature
from rag.vector_store import get_index_path, open_index, validate_index
from rag.retriever import retrieve


def main():
    parser = argparse.ArgumentParser(description="检索菜谱原文，显示余弦距离和来源")
    parser.add_argument("question")
    parser.add_argument("--index", type=Path, default=get_index_path())
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--max-distance", type=float, default=None)
    args = parser.parse_args()
    if not args.question.strip() or args.k < 1:
        parser.error("问题不能为空，k 必须大于 0")
    if args.max_distance is not None and not 0 <= args.max_distance <= 2:
        parser.error("余弦距离阈值必须在 0 到 2 之间")
    model_path = get_model_path()
    signature = model_signature(model_path)
    validate_index(args.index, signature)
    store = open_index(create_embedder(model_path), args.index, signature)
    results = retrieve(store, args.question, args.k, args.max_distance)
    print(f"检索到 {len(results)} 块；距离越小越相似，不是置信度概率。")
    for rank, (document, distance) in enumerate(results, 1):
        print(f"\n[{rank}] 余弦距离={distance:.4f}")
        print(f"来源：{document.metadata['source']}")
        print(document.page_content)


if __name__ == "__main__":
    main()
