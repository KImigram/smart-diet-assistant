# -*- coding: utf-8 -*-
"""
营养知识库构建脚本（借鉴 CookHero scripts/howtocook_loader.py 的设计思路）
============================================================
数据源：Anduin2017/HowToCook（MIT 协议）—— 392 个菜谱 markdown
流程：扫描 dishes/**/*.md → 解析菜名/菜系/难度/卡路里/原料/步骤
      → Ollama bge-m3 embedding → 存入 Chroma 持久化向量库

用法（在 backend 目录下执行）：
    python scripts/build_knowledge_base.py
"""
import re
import os
import sys
import time
from pathlib import Path

import requests

# ---------------- 配置 ----------------
# Temporary legacy builder. The new RAG pipeline will replace this script.
BACKEND_DIR = Path(__file__).resolve().parent.parent
KB_SOURCE = Path(
    os.getenv("RAG_KNOWLEDGE_SOURCE")
    or str(BACKEND_DIR / "data" / "knowledge_source")
)
KB_DIR = Path(
    os.getenv("RAG_VECTOR_DB_PATH") or str(BACKEND_DIR / "data" / "vector_db")
)
# Ollama embedding 模型
EMBED_MODEL = "bge-m3"
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434") + "/api/embed"
COLLECTION = "nutrition_knowledge"
# embedding 批量大小
BATCH = 32

CATEGORY_NAMES = {
    "aquatic": "水产海鲜", "breakfast": "早餐", "condiment": "酱料",
    "dessert": "甜品", "drink": "饮品", "meat_dish": "肉菜",
    "semi-finished": "半成品", "soup": "汤羹", "staple": "主食",
    "vegetable_dish": "素菜", "template": "模板",
}


def parse_markdown(path: Path) -> dict | None:
    """解析单个菜谱 markdown，返回结构化字典"""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None
    if not text.strip():
        return None

    lines = text.splitlines()
    title = ""
    intro_lines: list[str] = []
    sections: dict[str, list[str]] = {}
    current: str | None = None

    for line in lines:
        line = line.strip()
        if line.startswith("# "):
            title = line[2:].strip()
            # 去掉"的做法/家常做法"等后缀
            title = re.sub(r"的(做法|家常做法|烹饪方法|简单做法)$", "", title)
        elif line.startswith("## "):
            current = line[3:].strip()
            sections.setdefault(current, [])
        else:
            if current:
                if line:
                    sections[current].append(line)
            elif line:
                intro_lines.append(line)

    if not title:
        title = path.stem

    # 从简介提取难度与卡路里
    intro_text = " ".join(intro_lines)
    cal_match = re.search(r"预计卡路里[：:]\s*(\d+)\s*大卡", intro_text)
    diff_match = re.search(r"预计(?:烹饪)?难度[：:]\s*(.+)", intro_text)
    calorie = int(cal_match.group(1)) if cal_match else None
    difficulty = diff_match.group(1).strip() if diff_match else ""

    # 组装检索文本（去掉模板类文件）
    if title in ("菜谱模板", "模板", "Template"):
        return None

    content_parts = [f"菜名：{title}"]
    if intro_lines:
        content_parts.append("简介：" + " ".join(intro_lines[:6]))
    if difficulty:
        content_parts.append(f"难度：{difficulty}")
    if calorie:
        content_parts.append(f"预估热量：{calorie} 大卡")
    for sec_name, sec_lines in sections.items():
        body = "；".join(sec_lines[:40])
        if body:
            content_parts.append(f"{sec_name}：{body}")
    content = "\n".join(content_parts)

    return {
        "id": title,
        "dish_name": title,
        # HowToCook 目录两级：dishes/一级菜系/二级菜名/xxx.md
        "category": (
            CATEGORY_NAMES.get(path.parent.parent.name, path.parent.parent.name)
            if path.parent.parent.name in CATEGORY_NAMES
            else CATEGORY_NAMES.get(path.parent.name, path.parent.name)
        ),
        "difficulty": difficulty,
        "calorie": calorie,
        "source": str(path).replace(str(KB_SOURCE), "").lstrip("\\/"),
        "content": content,
    }


def embed_batch(texts: list[str]) -> list[list[float]]:
    """调用 Ollama bge-m3 批量向量化；单条失败时逐条降级重试"""
    try:
        resp = requests.post(OLLAMA_URL, json={"model": EMBED_MODEL, "input": texts}, timeout=120)
        resp.raise_for_status()
        return resp.json()["embeddings"]
    except Exception:
        # 批量失败 → 逐条重试，跳过坏数据
        result = []
        for t in texts:
            try:
                r = requests.post(OLLAMA_URL, json={"model": EMBED_MODEL, "input": [t]}, timeout=60)
                r.raise_for_status()
                result.append(r.json()["embeddings"][0])
            except Exception as e:
                print(f"  ⚠️ 跳过无法向量化的条目（{str(e)[:80]}）：{t[:40]}...")
                result.append(None)
        return result


def main():
    print(f"知识库源：{KB_SOURCE}")
    print(f"向量库目录：{KB_DIR}")

    md_files = sorted(list((KB_SOURCE / "dishes").rglob("*.md")))
    md_files += sorted(list((KB_SOURCE / "tips").rglob("*.md")))
    print(f"扫描到 {len(md_files)} 个 markdown 文件")

    docs = []
    for p in md_files:
        d = parse_markdown(p)
        if d:
            docs.append(d)
    print(f"解析成功 {len(docs)} 个知识条目（跳过模板/无法解析）")

    # 去重（同名菜谱）
    seen = set()
    unique = []
    for d in docs:
        if d["id"] not in seen:
            seen.add(d["id"])
            unique.append(d)
    docs = unique
    print(f"去重后 {len(docs)} 个知识条目")

    import chromadb
    client = chromadb.PersistentClient(path=str(KB_DIR))
    # 重建集合（重新构建时清空旧数据）
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    collection = client.get_or_create_collection(
        COLLECTION, metadata={"hnsw:space": "cosine"}
    )

    # 分批 embedding + 写入
    total = len(docs)
    t0 = time.time()
    for i in range(0, total, BATCH):
        batch = docs[i:i + BATCH]
        texts = [d["content"][:2000] for d in batch]  # 截断防超长
        embeddings = embed_batch(texts)
        # 过滤向量化失败的条目
        ok_batch = [(d, emb) for d, emb in zip(batch, embeddings) if emb is not None]
        if not ok_batch:
            continue
        collection.add(
            ids=[d["id"] for d, _ in ok_batch],
            embeddings=[emb for _, emb in ok_batch],
            documents=[d["content"][:2000] for d, _ in ok_batch],
            metadatas=[{
                "dish_name": d["dish_name"],
                "category": d["category"],
                "difficulty": d["difficulty"] or "未知",
                "calorie": d["calorie"] if d["calorie"] is not None else 0,
                "source": d["source"],
            } for d, _ in ok_batch],
        )
        done = min(i + BATCH, total)
        print(f"  已写入 {done}/{total}（{time.time() - t0:.0f}s）")

    print(f"\n✅ 构建完成：{total} 条知识入库 {KB_DIR}")
    print("  集合:", COLLECTION, "| embedding:", EMBED_MODEL)


if __name__ == "__main__":
    main()
