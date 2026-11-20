"""Evaluate retrieval; rewrite adapters optionally call cloud query rewriting."""

import argparse
import importlib
import json
import math
import platform
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals.benchmark import aggregate, compile_labels, digest, load_cases, rank_metrics
from rag.document_loader import load_recipe_documents
from rag.chunker import split_recipe_documents


def percentile(values, quantile):
    if not values:
        return None
    values = sorted(values)
    return values[max(0, math.ceil(quantile * len(values)) - 1)]


def main():
    parser = argparse.ArgumentParser(description="固定菜谱检索评测；正式运行会加载本地模型")
    dataset_args = parser.add_mutually_exclusive_group()
    dataset_args.add_argument("--questions", type=Path, help="自定义题库路径")
    dataset_args.add_argument("--suite", choices=['regression', 'expanded', 'multifact'], default=None,
                              help="regression 原90题；expanded 扩展200题（默认）；multifact 多事实专项")
    parser.add_argument('--cohort', choices=['all', 'regression', 'new'], default='all',
                        help='只运行旧题或新增题，默认全部')
    parser.add_argument('--category', nargs='+', help='只运行指定问题类别')
    parser.add_argument("--validate-only", action="store_true", help="只校验题库证据，不加载模型")
    parser.add_argument("--split", choices=["dev", "test", "all"], default="dev")
    parser.add_argument("--mode", choices=["raw", "oracle"], default="raw",
                        help="raw 使用当前问题；oracle 对追问题使用人工完整问题，非真实改写能力")
    parser.add_argument("--ks", type=int, nargs="+", default=[1, 3, 5])
    parser.add_argument("--adapter", default="evals.adapters:create_dense", help="module:factory；工厂接收 options 字典")
    parser.add_argument("--options", default="{}", help='适配器配置 JSON，如 {"max_distance":0.5}')
    parser.add_argument("--max-distance", type=float, help="仅用于默认稠密检索，便于 PowerShell 配置阈值")
    parser.add_argument("--size", type=int, default=500)
    parser.add_argument("--overlap", type=int, default=80)
    parser.add_argument("--output", type=Path, help="新的输出目录，默认 evals/outputs/时间戳")
    args = parser.parse_args()
    if args.questions is None:
        filename = {'regression':'rag_questions_v2.jsonl', 'multifact':'rag_multifact_v1.jsonl'}.get(args.suite, 'rag_questions_v3.jsonl')
        args.questions = Path(__file__).with_name(filename)
    ks = sorted(set(args.ks))
    if not ks or min(ks) < 1:
        parser.error("K 必须为正整数")
    options = json.loads(args.options)
    if not isinstance(options, dict):
        parser.error("options 必须是 JSON 对象")
    if args.adapter in {'evals.adapters:create_bm25', 'evals.adapters:create_rewrite_bm25'}:
        # Lexical-only adapters build from source and must use the evaluated chunking.
        options.update(size=args.size, overlap=args.overlap)
    if args.max_distance is not None:
        if args.adapter != "evals.adapters:create_dense":
            if args.adapter != "evals.adapters:create_rewrite_dense":
                parser.error("--max-distance 仅适用于稠密或改写加稠密检索；其他适配器请通过 options 配置")
        if not 0 <= args.max_distance <= 2:
            parser.error("余弦距离阈值必须在 0 到 2 之间")
        options["max_distance"] = args.max_distance
    cases = load_cases(args.questions)
    chunks = split_recipe_documents(load_recipe_documents(), args.size, args.overlap)
    labels = compile_labels(cases, chunks)
    corpus = {d.metadata["chunk_id"]: {"source": d.metadata["local_path"], "content": d.page_content} for d in chunks}
    print(f"题库 {len(cases)} 题，文本块 {len(chunks)}；类别：{dict(Counter(c['category'] for c in cases))}")
    if args.validate_only:
        print("全部原文证据匹配通过；未加载模型。")
        return
    if args.category:
        unknown = set(args.category) - {case['category'] for case in cases}
        if unknown:
            parser.error(f'未知问题类别：{sorted(unknown)}')
    selected = [c for c in cases
                if (args.split == "all" or c["split"] == args.split)
                and (args.cohort == 'all' or c.get('cohort', 'regression') == args.cohort)
                and (not args.category or c['category'] in args.category)]
    if not selected:
        parser.error("选中的划分没有问题")
    output = args.output or Path(__file__).parent / "outputs" / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    if output.exists():
        parser.error("输出目录已存在，请指定新目录，避免覆盖报告")
    module, factory = args.adapter.split(":", 1)
    print("正在初始化检索器、加载本地模型并打开索引，请等待……", flush=True)
    start = time.perf_counter()
    adapter = getattr(importlib.import_module(module), factory)(options)
    startup_ms = (time.perf_counter() - start) * 1000
    print(f"检索器初始化完成，耗时 {startup_ms/1000:.1f} 秒", flush=True)
    # Persisted dense index must exactly match current chunks before scoring.
    if hasattr(adapter, "store"):
        saved = adapter.store.get(include=["documents", "metadatas"])
        actual = {m["chunk_id"]: {"source": m["local_path"], "content": text}
                  for m, text in zip(saved["metadatas"], saved["documents"])}
        if actual != corpus:
            raise ValueError("索引与当前文本块不一致，禁止对过期索引计分")
    rows = []
    for i, case in enumerate(selected, 1):
        question = case.get("oracle_question", case["question"]) if args.mode == "oracle" else case["question"]
        start = time.perf_counter()
        error = None
        hits = []
        adapter.last_rewrite = None
        try:
            result = adapter.retrieve(question, case["history"], max(ks))
            seen = set()
            for hit in result:
                identity = hit["chunk_id"]
                if identity not in corpus or hit["source"] != corpus[identity]["source"] or hit["content"] != corpus[identity]["content"]:
                    raise ValueError("适配器返回了当前评测语料之外的文本或编号")
                if not isinstance(hit["accepted"], bool):
                    raise ValueError("accepted 必须为 bool")
                if identity not in seen:
                    hits.append(hit)
                    seen.add(identity)
            hits = hits[:max(ks)]
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            hits = []
        elapsed_ms = (time.perf_counter() - start) * 1000
        accepted = [h for h in hits if h["accepted"]]
        row = {"id": case["id"], "category": case["category"], "answerable": case["answerable"],
               'cohort': case.get('cohort', 'regression'),
               'negative_kind': case.get('negative_kind', 'legacy_unspecified') if not case['answerable'] else None,
               "question": case["question"], "effective_question": question, "history": case["history"],
               "evidence": case["evidence"], "raw_hits": hits, "accepted": accepted,
               "gold_chunk_ids": sorted(labels[case["id"]]["relevant"]),
               "gold_evidence_groups": [sorted(g) for g in labels[case["id"]]["groups"]],
               "raw_metrics": rank_metrics(hits, labels[case["id"]], ks),
               "accepted_metrics": rank_metrics(accepted, labels[case["id"]], ks),
               "elapsed_ms": elapsed_ms, "error": error}
        row['rewrite'] = getattr(adapter, 'last_rewrite', None)
        row['retrieval_question'] = row['rewrite']['query'] if row['rewrite'] else question
        rows.append(row)
        print(f"[{i}/{len(selected)}] {case['id']} {'ERROR' if error else 'OK'} {elapsed_ms:.0f}ms", flush=True)
    summary = aggregate(rows, ks)
    groups = {category: aggregate([r for r in rows if r["category"] == category], ks)
              for category in sorted({r["category"] for r in rows})}
    try:
        git_revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[2], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        git_revision = "unknown"
    tracked_code = [Path(__file__), Path(__file__).with_name("benchmark.py"), Path(__file__).with_name("adapters.py")]
    tracked_code += list((Path(__file__).resolve().parents[1] / "rag").glob("*.py"))
    report = {"schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
              "dataset_hash": digest(cases), "corpus_hash": digest(corpus),
              "case_ids": [c["id"] for c in selected], "split": args.split, "mode": args.mode, "ks": ks,
              "adapter": args.adapter, "adapter_info": getattr(adapter, "info", {}), "options": options,
              "git_revision": git_revision, "code_hash": digest({str(p.relative_to(Path(__file__).resolve().parents[2])):p.read_text(encoding='utf-8') for p in tracked_code}),
              "python": platform.python_version(), "packages": {p: version(p) for p in ['torch','sentence-transformers','langchain-core','langchain-chroma','chromadb','rank-bm25','jieba']},
              "startup_ms": startup_ms, "first_query_ms": rows[0]["elapsed_ms"],
              "remaining_queries_p50_ms": percentile([r['elapsed_ms'] for r in rows[1:] if not r['error']], .5),
              "remaining_queries_p95_ms": percentile([r['elapsed_ms'] for r in rows[1:] if not r['error']], .95),
              "summary": summary, "by_category": groups, "rows": rows}
    report['selection'] = {'suite': args.suite or ('custom' if args.questions.name not in {'rag_questions_v2.jsonl', 'rag_questions_v3.jsonl'} else args.questions.stem),
                           'questions_file': str(args.questions), 'cohort': args.cohort, 'categories': args.category}
    report['by_cohort'] = {cohort: aggregate([row for row in rows if row['cohort'] == cohort], ks)
                           for cohort in sorted({row['cohort'] for row in rows})}
    report['by_negative_kind'] = {kind: aggregate([row for row in rows if row['negative_kind'] == kind], ks)
                                  for kind in sorted({row['negative_kind'] for row in rows if row['negative_kind']})}
    report['rewrite_summary'] = {
        'attempted':sum(bool(r['rewrite']) and r['rewrite']['status'] != 'no_history' for r in rows),
        'changed':sum(bool(r['rewrite']) and r['rewrite']['changed'] for r in rows),
        'fallbacks':sum(bool(r['rewrite']) and r['rewrite']['status'] == 'fallback' for r in rows),
    }
    output.mkdir(parents=True)
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# Retrieval evaluation / 检索评测", "", f"split={args.split}, mode={args.mode}",
             "", "| K | 至少一份证据命中 | 全部证据命中 | 证据组覆盖率 | 菜谱命中 | 证据召回 | 精确率 | MRR | nDCG |", "|---|---|---|---|---|---|---|---|---|"]
    for k, metric in summary['accepted_metrics'].items():
        lines.append("| " + k + " | " + " | ".join(f"{metric.get(name,0):.4f}" for name in ['evidence_hit','all_evidence_hit','evidence_group_coverage','document_hit','evidence_recall','evidence_precision','mrr','ndcg']) + " |")
    lines += ["", f"无答案题拒绝率：{summary['negative_rejection_rate']}",
              f"有答案题空结果率：{summary['positive_empty_rate']}", f"错误数：{summary['errors']}",
              "", "拒绝率只评价检索过滤，不代表生成模型已正确拒答。逐题原文、分数和错误见 report.json。"]
    for title, breakdown in [('旧题/新题', report['by_cohort']), ('问题类别', groups)]:
        lines += ['', f'## {title}', '', '| 类别 | 题数 | 有答案 | Top-1证据命中 | Top-3证据命中 | 错误数 |',
                  '|---|---|---|---|---|---|']
        for name, result in breakdown.items():
            def hit_at(k):
                value = result['accepted_metrics'].get(str(k), {}).get('evidence_hit')
                return f'{value:.2%}' if value is not None else '—'
            lines.append(f"| {name} | {result['questions']} | {result['answerable']} | {hit_at(1)} | {hit_at(3)} | {result['errors']} |")
    if report['by_negative_kind']:
        lines += ['', '## 无答案场景', '', '| 类型 | 题数 | 检索拒绝率 |', '|---|---|---|']
        for kind, result in report['by_negative_kind'].items():
            lines.append(f"| {kind} | {result['questions']} | {result['negative_rejection_rate']:.2%} |")
    if report['rewrite_summary']['attempted']:
        lines += ["", "## 查询改写", "", str(report['rewrite_summary']), "",
                  "| 题号 | 原问题 | 检索问题 | 状态 | 改写耗时 ms |", "|---|---|---|---|---|"]
        for row in rows:
            trace = row['rewrite']
            if trace and trace['status'] != 'no_history':
                original = row['question'].replace('|','／').replace('\n',' ')
                query = trace['query'].replace('|','／').replace('\n',' ')
                lines.append(f"| {row['id']} | {original} | {query} | {trace['status']} | {trace['elapsed_ms']:.0f} |")
    (output / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"报告：{output.resolve()}")
    if summary['errors']:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
