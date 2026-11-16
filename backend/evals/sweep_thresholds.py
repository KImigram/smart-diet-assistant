"""Replay cosine thresholds on saved dense candidates, without model inference."""

import argparse
import copy
import json
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evals.benchmark import aggregate, rank_metrics


def sweep(report: dict, thresholds: list[float], k: int = 3) -> list[dict]:
    if report['adapter_info'].get('score_type') != 'cosine_distance_lower_is_better':
        raise ValueError('只允许对余弦距离报告回放阈值')
    if report['summary']['errors']:
        raise ValueError('原报告包含错误，请先排查')
    if k < 1 or k > max(report['ks']):
        raise ValueError('K 超出原报告候选池范围')
    if any(not 0 <= t <= 2 for t in thresholds):
        raise ValueError('余弦距离阈值必须在 0 到 2 之间')
    results = []
    for threshold in [None, *sorted(set(thresholds))]:
        rows = []
        for original in report['rows']:
            row = copy.deepcopy(original)
            hits = [h for h in row['raw_hits'] if threshold is None or h['score'] <= threshold][:k]
            row['accepted'] = hits
            label = {'relevant':set(row['gold_chunk_ids']),
                     'groups':[set(g) for g in row['gold_evidence_groups']],
                     'sources':{e['source'] for e in row['evidence']}}
            row['raw_metrics'] = rank_metrics(row['raw_hits'], label, [k])
            row['accepted_metrics'] = rank_metrics(hits, label, [k])
            rows.append(row)
        summary = aggregate(rows, [k])
        metric = summary['accepted_metrics'][str(k)]
        results.append({'threshold':threshold, 'k':k, 'summary':summary,
                        'evidence_hit':metric.get('evidence_hit'),
                        'group_coverage':metric.get('evidence_group_coverage'),
                        'positive_hit_ids':[r['id'] for r in rows if r['answerable'] and r['accepted_metrics'][str(k)]['evidence_hit']],
                        'positive_miss_ids':[r['id'] for r in rows if r['answerable'] and not r['accepted_metrics'][str(k)]['evidence_hit']],
                        'positive_empty_ids':[r['id'] for r in rows if r['answerable'] and not r['accepted']],
                        'negative_rejected_ids':[r['id'] for r in rows if not r['answerable'] and not r['accepted']],
                        'negative_accepted_ids':[r['id'] for r in rows if not r['answerable'] and r['accepted']]})
    return results


def render(results: list[dict]) -> str:
    lines = ['# 开发集阈值回放', '', '使用已保存候选重新过滤，无需重复加载模型；不是新的独立推理实验。', '',
             '| 最大余弦距离 | 证据命中 | 无答案过滤 | 有答案空结果 |', '|---|---|---|---|']
    for row in results:
        summary = row['summary']
        lines.append(f"| {row['threshold'] if row['threshold'] is not None else '不限制'} | {len(row['positive_hit_ids'])}/{summary['answerable']} ({row['evidence_hit']:.1%}) | {len(row['negative_rejected_ids'])}/{summary['unanswerable']} | {len(row['positive_empty_ids'])}/{summary['answerable']} |")
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='从稠密检索报告回放距离阈值，不加载模型')
    parser.add_argument('report', type=Path)
    parser.add_argument('--thresholds', type=float, nargs='+', default=[.35,.375,.4,.425,.45,.475,.5,.55])
    parser.add_argument('--k', type=int, default=3)
    parser.add_argument('--output', type=Path, required=True, help='新的输出目录')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('输出目录已存在，禁止覆盖')
    report = json.loads(args.report.read_text(encoding='utf-8'))
    results = sweep(report, args.thresholds, args.k)
    args.output.mkdir(parents=True)
    payload = {'source_report':str(args.report.resolve()), 'dataset_hash':report['dataset_hash'],
               'corpus_hash':report['corpus_hash'], 'mode':report['mode'], 'split':report['split'],
               'candidate_pool_k':max(report['ks']), 'results':results}
    (args.output/'thresholds.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    text = render(results)
    (args.output/'thresholds.md').write_text(text,encoding='utf-8')
    print(text)


if __name__ == '__main__':
    main()
