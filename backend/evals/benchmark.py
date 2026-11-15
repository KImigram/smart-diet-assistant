"""Evidence-grounded labels and deterministic retrieval metrics."""

import hashlib
import json
import math
import re
from pathlib import Path


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def normalize(text: str) -> str:
    return re.sub(r"[\W_]+", "", text).lower()


def load_cases(path: Path) -> list[dict]:
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = set()
    sources = {}
    for case in cases:
        if case["id"] in ids or not case["question"].strip():
            raise ValueError("题号重复或问题为空")
        ids.add(case["id"])
        if case["split"] not in {"dev", "test"}:
            raise ValueError("未知数据划分")
        if not isinstance(case["answerable"], bool) or bool(case["evidence"]) != case["answerable"]:
            raise ValueError("有答案题必须有证据，无答案题证据应为空")
        for evidence in case["evidence"]:
            source = evidence["source"]
            if sources.setdefault(source, case["split"]) != case["split"]:
                raise ValueError(f"同一道菜不能跨 dev/test 划分：{source}")
    return cases


def compile_labels(cases: list[dict], chunks: list) -> dict:
    """Match declared source/section/quote locators to the CURRENT chunk corpus.

    This labels annotated evidence, not every semantically related passage.
    Failure to match is a dataset error, never silently skipped.
    """
    labels = {}
    for case in cases:
        groups = []
        for evidence in case["evidence"]:
            quote = normalize(evidence["quote"])
            if not quote:
                raise ValueError(f"{case['id']}: empty evidence quote")
            matches = {
                chunk.metadata["chunk_id"] for chunk in chunks
                if chunk.metadata["local_path"] == evidence["source"]
                and chunk.metadata["section"] == evidence["section"]
                and quote in normalize(chunk.page_content)
            }
            if not matches:
                raise ValueError(f"{case['id']}: 原文证据无法匹配当前分块：{evidence}")
            groups.append(matches)
        labels[case["id"]] = {
            "groups": groups,
            "relevant": set().union(*groups) if groups else set(),
            "sources": {e["source"] for e in case["evidence"]},
        }
    return labels


def rank_metrics(hits: list[dict], label: dict, ks: list[int]) -> dict:
    """Binary annotated-evidence relevance; duplicate IDs count only once."""
    unique = []
    seen = set()
    for hit in hits:
        if hit["chunk_id"] not in seen:
            unique.append(hit)
            seen.add(hit["chunk_id"])
    gold = label["relevant"]
    metrics = {}
    for k in ks:
        ranked = unique[:k]
        ids = {h["chunk_id"] for h in ranked}
        relevant = [h["chunk_id"] in gold for h in ranked]
        matched = len(ids & gold)
        dcg = sum(1 / math.log2(i + 2) for i, yes in enumerate(relevant) if yes)
        ideal = sum(1 / math.log2(i + 2) for i in range(min(k, len(gold))))
        metrics[str(k)] = {
            "evidence_hit": float(matched > 0),
            "document_hit": float(any(h["source"] in label["sources"] for h in ranked)),
            "evidence_recall": matched / len(gold) if gold else 0.0,
            "evidence_precision": matched / k,
            "mrr": next((1 / (i + 1) for i, yes in enumerate(relevant) if yes), 0.0),
            "ndcg": dcg / ideal if ideal else 0.0,
            "evidence_group_coverage": sum(bool(ids & g) for g in label["groups"]) / len(label["groups"]) if label["groups"] else 0.0,
        }
    return metrics


def aggregate(rows: list[dict], ks: list[int]) -> dict:
    positives = [r for r in rows if r["answerable"]]
    negatives = [r for r in rows if not r["answerable"]]
    summary = {"questions": len(rows), "answerable": len(positives), "unanswerable": len(negatives),
               "errors": sum(r["error"] is not None for r in rows)}
    for field in ("raw_metrics", "accepted_metrics"):
        summary[field] = {
            str(k): {metric: sum(r[field][str(k)][metric] for r in positives) / len(positives)
                     for metric in positives[0][field][str(k)]} if positives else {}
            for k in ks
        }
    summary["negative_rejection_rate"] = (
        sum(not r["error"] and not r["accepted"] for r in negatives) / len(negatives)
        if negatives else None
    )
    summary["positive_empty_rate"] = (
        sum(not r["error"] and not r["accepted"] for r in positives) / len(positives)
        if positives else None
    )
    return summary
