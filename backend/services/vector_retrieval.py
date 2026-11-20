# -*- coding: utf-8 -*-
"""
向量检索服务（营养知识库 · 借鉴 CookHero 混合检索的向量路）
============================================================
流程：问题 → Ollama bge-m3 embedding → Chroma 余弦相似度检索 top-k 知识块

与 rag_service.py 的结构化检索（MySQL 用户数据）互为补充：
- 结构化：用户档案 / 饮食记录 / 体重（精确、实时、个性化）
- 向量化：菜谱 / 营养知识库（语义相似、覆盖面广）

任何一步不可用（未建库 / Ollama 未启动）都返回空列表，不阻塞主流程。
"""
from pathlib import Path

import requests

# 向量库持久化目录（与构建脚本一致）
KB_DIR = Path(__file__).resolve().parent.parent / "data" / "knowledge_db"
COLLECTION = "nutrition_knowledge"
EMBED_MODEL = "bge-m3"
from config import OLLAMA_BASE_URL

OLLAMA_EMBED_URL = OLLAMA_BASE_URL + "/api/embed"

_client = None
_collection = None


def _get_collection():
    """懒加载 Chroma 集合（避免每次查询重新打开）"""
    global _client, _collection
    if _collection is not None:
        return _collection
    try:
        import chromadb
        _client = chromadb.PersistentClient(path=str(KB_DIR))
        _collection = _client.get_collection(COLLECTION)
    except Exception:
        _collection = None
    return _collection


def embed_text(text: str) -> list[float] | None:
    """单条文本向量化"""
    try:
        resp = requests.post(
            OLLAMA_EMBED_URL,
            json={"model": EMBED_MODEL, "input": [text]},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["embeddings"][0]
    except Exception:
        return None


class VectorRetrieval:
    """营养知识库向量检索"""

    @staticmethod
    def query(question: str, top_k: int = 3) -> list[dict]:
        """
        语义检索知识库，返回 top-k 条知识块。
        返回：[{dish_name, category, difficulty, calorie, source, content, distance}]
        """
        collection = _get_collection()
        if collection is None:
            return []

        query_vec = embed_text(question)
        if query_vec is None:
            return []

        try:
            res = collection.query(
                query_embeddings=[query_vec],
                n_results=min(top_k, 10),
                include=["documents", "metadatas", "distances"],
            )
        except Exception:
            return []

        results = []
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
        for doc, meta, dist in zip(docs, metas, dists):
            results.append({
                "dish_name": (meta or {}).get("dish_name", ""),
                "category": (meta or {}).get("category", ""),
                "difficulty": (meta or {}).get("difficulty", ""),
                "calorie": (meta or {}).get("calorie", 0),
                "source": (meta or {}).get("source", ""),
                "content": doc,
                "distance": round(float(dist), 4),
            })
        return results


if __name__ == "__main__":
    # 自测
    tests = ["红烧肉怎么做", "减脂期适合吃什么早餐", "清蒸鲈鱼的步骤", "西红柿炒鸡蛋热量"]
    for q in tests:
        hits = VectorRetrieval.query(q, top_k=2)
        print(f"\n问：{q}")
        for h in hits:
            print(f"  [{h['distance']}] {h['dish_name']}（{h['category']}）"
                  f"热量{h['calorie']}大卡 难度{h['difficulty']}")
