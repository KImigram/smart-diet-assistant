"""Load curated recipe Markdown files as LangChain documents.

The source Markdown is kept unchanged. Cleaning happens while loading so the
index can be rebuilt reproducibly whenever the rules change.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from langchain_core.documents import Document


BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_RECIPES_DIR = (
    BACKEND_DIR / "data" / "knowledge_source" / "howtocook" / "recipes"
)

REQUIRED_METADATA = {
    "title",
    "category",
    "source_project",
    "source_path",
    "source_url",
    "license",
}

# define capture info from source data
FRONT_MATTER_PATTERN = re.compile(
    r"\A---\s*\r?\n(?P<metadata>.*?)\r?\n---\s*(?:\r?\n|\Z)(?P<body>.*)\Z",
    re.DOTALL,
)# DOTALL .能包含换行符 读取多行内容
IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\([^)]*\)|<img\b[^>]*>", re.IGNORECASE)
UNRELIABLE_LINE_PATTERN = re.compile(r"^预估(?:烹饪)?(?:难度|卡路里)[：:].*$")
CONTRIBUTION_PATTERN = re.compile(
    r"如果您遵循本指南.*(?:Issue|Pull\s*request)", re.IGNORECASE
)
# IGNORECASE 忽略大小写

# 异常类 值异常时报错为RecipeDocumentError
class RecipeDocumentError(ValueError):
    """Raised when a curated recipe file does not match the expected format."""


def _parse_markdown(path: Path) -> tuple[dict[str, Any], str]:
    """Parse YAML front matter and Markdown body from one recipe file."""
    text = path.read_text(encoding="utf-8")
    match = FRONT_MATTER_PATTERN.match(text)
    if not match:
        raise RecipeDocumentError(f"{path}: YAML front matter 格式不正确")

    metadata = yaml.safe_load(match.group("metadata"))
    if not isinstance(metadata, dict):
        raise RecipeDocumentError(f"{path}: YAML front matter 必须是键值对象")

    missing = sorted(REQUIRED_METADATA - metadata.keys())
    if missing:
        raise RecipeDocumentError(f"{path}: 缺少元数据字段 {', '.join(missing)}")

    return metadata, match.group("body")


def _clean_recipe_body(body: str) -> str:
    """Keep recipe facts while removing unverified preamble and boilerplate."""
    body = body.replace("\r\n", "\n").replace("\r", "\n") # 统一换行符
    lines = body.splitlines()  # 按行切分文本 输出一个列表 一行作为一个元素

    cleaned: list[str] = []
    seen_title = False
    reached_first_section = False

    for line in lines:
        stripped = line.strip()   # strip() 去掉字符串两边空白

        if stripped.startswith("# ") and not seen_title:
            seen_title = True
            cleaned.append(line.rstrip())  # rstrip去掉右边空白 防止删去缩进
            continue

        if seen_title and not reached_first_section:
            if stripped.startswith("## "):
                reached_first_section = True
                cleaned.append("")
                cleaned.append(line.rstrip())
            # Drop the free-form introduction, difficulty and calorie estimate.
            continue

        if UNRELIABLE_LINE_PATTERN.match(stripped):
            continue
        if CONTRIBUTION_PATTERN.search(stripped):
            continue

        without_images = IMAGE_PATTERN.sub("", line).rstrip()
        if without_images.strip():
            cleaned.append(without_images)
        elif cleaned and cleaned[-1] != "":
            cleaned.append("")

    result = "\n".join(cleaned).strip()
    result = re.sub(r"\n{3,}", "\n\n", result)

    if not seen_title:
        raise RecipeDocumentError("菜谱正文缺少一级标题")
    if not reached_first_section:
        raise RecipeDocumentError("菜谱正文缺少二级章节")
    if not result:
        raise RecipeDocumentError("清洗后的菜谱正文为空")

    return result


def _build_metadata(raw: dict[str, Any], path: Path, root: Path) -> dict[str, Any]:
    """Create portable scalar metadata suitable for a vector store."""
    category = str(raw["category"])
    if category != path.parent.name:
        raise RecipeDocumentError(
            f"{path}: category={category!r} 与目录 {path.parent.name!r} 不一致"
        )

    # Chroma metadata values should be scalar, so normalize every value here.
    # scaler标量 数据库内只能是标量 不能是列表或字典等
    metadata = {key: str(value) for key, value in raw.items()}
    metadata.update(
        {
            "source": str(raw["source_url"]),
            "local_path": path.relative_to(root).as_posix(),   # path.relative_to()求对于参数的相对路径；as_posix强制使用正斜杠/
            "document_type": "recipe",
        }  # update() 更新字典的内容的函数
    )
    return metadata


def load_recipe_documents(
    recipes_dir: str | Path = DEFAULT_RECIPES_DIR,
) -> list[Document]:
    """Load every curated recipe under ``recipes_dir`` in deterministic order."""
    root = Path(recipes_dir).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"菜谱目录不存在: {root}")

    paths = sorted(root.rglob("*.md"), key=lambda item: item.as_posix())
    if not paths:
        raise RecipeDocumentError(f"菜谱目录中没有 Markdown 文件: {root}")

    documents: list[Document] = []
    for path in paths:
        try:
            raw_metadata, body = _parse_markdown(path)
            cleaned_body = _clean_recipe_body(body)
            metadata = _build_metadata(raw_metadata, path, root)
        except (OSError, yaml.YAMLError, RecipeDocumentError) as exc:
            if isinstance(exc, RecipeDocumentError):
                raise
            raise RecipeDocumentError(f"{path}: 加载失败: {exc}") from exc

        documents.append(Document(page_content=cleaned_body, metadata=metadata))

    return documents

