"""Check provenance, section boundaries and retention of recipe facts."""

import sys
from pathlib import Path

import pytest
from langchain_core.documents import Document

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from rag.chunker import split_recipe_documents  # noqa: E402


def test_sections_keep_provenance_and_original_document():
    original = Document(
        page_content="# 测试菜\n\n## 原料\n\n- 盐 2.5g\n- 鸡肉 200g\n\n## 操作\n\n蒸 10 分钟。",
        metadata={"title": "测试菜", "local_path": "meat/测试菜.md", "source": "example"},
    )
    chunks = split_recipe_documents([original])
    assert len(chunks) == 2
    assert [c.metadata["section"] for c in chunks] == ["原料", "操作"]
    assert "盐 2.5g" in chunks[0].page_content
    assert "蒸 10 分钟" in chunks[1].page_content
    assert all(c.metadata["source"] == "example" for c in chunks)
    assert all(c.page_content.startswith("菜名：测试菜\n章节：") for c in chunks)
    assert "chunk_id" not in original.metadata
    assert chunks == split_recipe_documents([original])


def test_long_section_keeps_all_facts_with_size_limit():
    facts = [f"步骤{i:03d}：加入食材{i:03d}，加热 3 分钟。" for i in range(40)]
    doc = Document(
        page_content="# 长菜谱\n\n## 操作\n\n" + "\n".join(facts),
        metadata={"title": "长菜谱", "local_path": "meat/长菜谱.md"},
    )
    chunks = split_recipe_documents([doc], chunk_size=140, chunk_overlap=30)
    assert len(chunks) > 1
    assert all(len(c.page_content) <= 140 for c in chunks)
    assert all(any(fact in c.page_content for c in chunks) for fact in facts)
    assert len({c.metadata["chunk_id"] for c in chunks}) == len(chunks)


@pytest.mark.parametrize("size,overlap", [(0, 0), (100, -1), (100, 100)])
def test_invalid_sizes(size, overlap):
    with pytest.raises(ValueError):
        split_recipe_documents([], size, overlap)
