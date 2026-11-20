"""Inspect chunk sizes, inherited metadata and complete chunk contents."""

import argparse
import statistics
import sys
from collections import Counter
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rag.chunker import split_recipe_documents  # noqa: E402
from rag.document_loader import load_recipe_documents  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="查看菜谱分块结果")
    parser.add_argument("--size", type=int, default=500, help="每块最大字符数，含菜名章节")
    parser.add_argument("--overlap", type=int, default=80, help="同章节相邻块目标重叠字符数")
    parser.add_argument("--show", type=int, default=3, help="展示前 N 块")
    parser.add_argument("--title", help="只展示指定菜名的文本块")
    args = parser.parse_args()

    documents = load_recipe_documents()
    chunks = split_recipe_documents(documents, args.size, args.overlap)
    lengths = [len(chunk.page_content) for chunk in chunks]
    counts = Counter(chunk.metadata["local_path"] for chunk in chunks)
    assert len(counts) == len(documents), "存在没有生成文本块的菜谱"
    assert max(lengths) <= args.size, "存在超出长度限制的文本块"
    assert len({chunk.metadata["chunk_id"] for chunk in chunks}) == len(chunks)
    print(f"菜谱数：{len(documents)}；文本块数：{len(chunks)}")
    print(f"字符数：最短={min(lengths)}，最长={max(lengths)}，平均={statistics.mean(lengths):.1f}")
    print(f"每篇块数：最少={min(counts.values())}，最多={max(counts.values())}")
    print("注意：字符数不是 token（模型词元）数；重叠只发生在同一章节内。")

    selected = [c for c in chunks if not args.title or c.metadata["title"] == args.title]
    if args.title and not selected:
        parser.error(f"没有找到菜谱：{args.title}")
    for chunk in selected[:max(0, args.show)]:
        print("\n" + "=" * 60)
        print(f"metadata（元数据）：{chunk.metadata}")
        print(f"page_content（正文内容），{len(chunk.page_content)} 字符：")
        print(chunk.page_content)


if __name__ == "__main__":
    main()
