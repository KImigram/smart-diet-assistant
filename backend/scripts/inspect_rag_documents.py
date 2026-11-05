"""Inspect recipe documents after loading and deterministic cleaning."""

from __future__ import annotations

import argparse
import statistics
import sys
from collections import Counter
from pathlib import Path


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from rag.document_loader import load_recipe_documents  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="检查 RAG 菜谱文档加载结果")
    parser.add_argument("--show", type=int, default=2, help="展示前 N 个文档")
    args = parser.parse_args()

    documents = load_recipe_documents()
    lengths = [len(document.page_content) for document in documents]
    categories = Counter(document.metadata["category"] for document in documents)

    print(f"加载文档数: {len(documents)}")
    print("分类统计:")
    for category, count in sorted(categories.items()):
        print(f"  {category}: {count}")
    print(
        "正文字符数: "
        f"min={min(lengths)}, max={max(lengths)}, "
        f"avg={statistics.mean(lengths):.1f}"
    )

    forbidden = ("预估卡路里", "预估烹饪难度", "Pull request")
    contaminated = [
        document.metadata["local_path"]
        for document in documents
        if any(term in document.page_content for term in forbidden)
    ]
    if contaminated:
        raise RuntimeError(f"清洗后仍存在不可靠内容: {contaminated}")

    for index, document in enumerate(documents[: max(args.show, 0)], start=1):
        print("\n" + "=" * 72)
        print(f"文档 {index}: {document.metadata['title']}")
        print("metadata:")
        for key, value in sorted(document.metadata.items()):
            print(f"  {key}: {value}")
        print("page_content:")
        print(document.page_content)


if __name__ == "__main__":
    main()

