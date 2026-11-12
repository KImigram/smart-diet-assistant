"""Local-only BGE-M3 adapter. Importing this module does not load a model."""

import hashlib
import json
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_DIR / ".env")


def get_model_path() -> Path:
    return Path(os.getenv("RAG_EMBEDDING_MODEL_PATH") or r"D:\models\bge-m3").resolve()


def model_signature(model_path: Path) -> str:
    """Detect local file/config changes; this is not a weight integrity check."""
    files = sorted(p for p in model_path.rglob("*") if p.is_file() and ".cache" not in p.parts)
    entries = []
    for path in files:
        if path.suffix not in {".json", ".bin", ".safetensors", ".model"}:
            continue
        stat = path.stat()
        entry = [path.relative_to(model_path).as_posix(), stat.st_size, stat.st_mtime_ns]
        if path.suffix == ".json":
            entry.append(hashlib.sha256(path.read_bytes()).hexdigest())
        entries.append(entry)
    return hashlib.sha256(json.dumps(entries).encode()).hexdigest()


def create_embedder(model_path: Path | None = None):
    """Explicit call loads local weights on CPU, with normalized dense vectors."""
    path = model_path or get_model_path()
    for filename in ("config.json", "modules.json", "tokenizer_config.json", "1_Pooling/config.json"):
        if not (path / filename).is_file():
            raise FileNotFoundError(f"缺少模型文件：{path / filename}")
    if not any((path / name).is_file() for name in ("model.safetensors", "pytorch_model.bin")):
        raise FileNotFoundError(f"没有找到模型主权重：{path}")

    import torch
    from packaging.version import Version

    if not (path / "model.safetensors").exists() and Version(torch.__version__.split("+")[0]) < Version("2.6"):
        raise RuntimeError(
            "当前权重为 pytorch_model.bin，需 PyTorch >= 2.6 才能通过 Transformers 安全检查。"
            "请先升级 rag 环境的 CPU PyTorch；程序不会绕过检查或自动下载权重。"
        )

    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name=str(path),
        model_kwargs={"device": "cpu", "local_files_only": True, "trust_remote_code": False},
        encode_kwargs={"normalize_embeddings": True, "batch_size": 4},
        query_encode_kwargs={"normalize_embeddings": True},
        show_progress=True,
    )
