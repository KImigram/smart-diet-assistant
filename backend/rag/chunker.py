"""Split recipes by Markdown headings, then split long sections by characters."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence

from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)


def split_recipe_documents(
    documents: Sequence[Document],
    chunk_size: int = 500,
    chunk_overlap: int = 80,
) -> list[Document]:
    """Return chunks with inherited sources and explicit dish/section context.

    Sizes are Python character counts, not token counts. The final content,
    including the context prefix, fits inside chunk_size. Overlap is a target
    within one section; heading boundaries are never crossed for overlap.
    """
    if chunk_size <= 0 or not 0 <= chunk_overlap < chunk_size:
        raise ValueError("要求 chunk_size > 0 且 0 <= chunk_overlap < chunk_size")

    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "recipe_heading"),
            ("##", "section"),
            ("###", "subsection"),
        ],
        strip_headers=True,
    )
    chunks: list[Document] = []

    for document in documents:
        title = document.metadata["title"]
        chunk_index = 0
        sections = header_splitter.split_text(document.page_content)

        for section in sections:
            if not section.page_content.strip():
                continue
            section_name = section.metadata.get("section", "正文")
            subsection = section.metadata.get("subsection")
            section_path = f"{section_name} / {subsection}" if subsection else section_name
            prefix = f"菜名：{title}\n章节：{section_path}\n\n"
            body_budget = chunk_size - len(prefix)
            if body_budget <= chunk_overlap:
                raise ValueError(f"{title}: 菜名和章节过长，请增大 chunk_size")

            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=body_budget,
                chunk_overlap=chunk_overlap,
                length_function=len,
                # Prefer paragraphs, then lines, then Chinese sentence boundaries.
                separators=["\n\n", "\n", "。", "；", "！", "？", "，", " ", ""],
                keep_separator="end",
            )
            for body in text_splitter.split_text(section.page_content):
                content = prefix + body
                metadata = {**document.metadata, **section.metadata}
                identity = (
                    f"{metadata['local_path']}\n{chunk_index}\n{content}"
                ).encode("utf-8")
                metadata.update(
                    section=section_name,
                    chunk_index=chunk_index,
                    chunk_id=hashlib.sha256(identity).hexdigest(),
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )
                chunks.append(Document(page_content=content, metadata=metadata))
                chunk_index += 1

    return chunks
