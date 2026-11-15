"""Compare reports only when the fixed questions and chunk corpus match."""

import argparse
import json
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


def compare(left: dict, right: dict, allow_mode_change=False) -> str:
    keys = ["schema_version", "dataset_hash", "corpus_hash", "case_ids", "ks", "split"]
    if not allow_mode_change:
        keys.append("mode")
    for key in keys:
        if left[key] != right[key]:
            raise ValueError(f"不可直接比较：{key} 不一致")
    lines = [f"A={left['adapter']} ({left['mode']})", f"B={right['adapter']} ({right['mode']})"]
    if left['mode'] != right['mode']:
        lines.append("注意：oracle 使用人工完整问题，仅作为参考上限，不代表自动问题改写已实现。")
    for k in left['ks']:
        for name in ["evidence_hit", "document_hit", "evidence_recall", "evidence_precision", "mrr", "ndcg", "evidence_group_coverage"]:
            a = left['summary']['accepted_metrics'][str(k)][name]
            b = right['summary']['accepted_metrics'][str(k)][name]
            lines.append(f"{name}@{k}: {a:.4f} -> {b:.4f} (delta={b-a:+.4f})")
    lines.append(f"错误数 A/B：{left['summary']['errors']}/{right['summary']['errors']}")
    for category in sorted(left['by_category'].keys() & right['by_category'].keys()):
        a = left['by_category'][category]['accepted_metrics'][str(max(left['ks']))].get('evidence_hit')
        b = right['by_category'][category]['accepted_metrics'][str(max(left['ks']))].get('evidence_hit')
        if a is not None and b is not None:
            lines.append(f"分类 {category} evidence_hit@{max(left['ks'])}: {a:.4f} -> {b:.4f}")
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description="对比两次固定检索评测报告")
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    parser.add_argument('--allow-mode-change', action='store_true')
    args = parser.parse_args()
    left, right = [json.loads(p.read_text(encoding='utf-8')) for p in [args.before, args.after]]
    print(compare(left, right, args.allow_mode_change))


if __name__ == '__main__':
    main()
