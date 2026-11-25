"""Evaluate spoken Chinese intent and rewriting without retrieval or answer generation."""
import argparse
from collections import Counter
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import re
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rag.query_plan import analyze_question
from rag.query_rewriter import create_rewrite_model
from services.structured_nutrition import resolve_period


def has_terms(value, groups):
    return all(any(term in (value or '') for term in group) for group in groups)


class RecordedModel:
    def __init__(self, model):
        self.model = model
        self.raw_plan = None

    def invoke(self, messages):
        self.raw_plan = None
        response = self.model.invoke(messages)
        self.raw_plan = response.content
        return response


def plan_checks(plan, expected, today):
    if plan is None:
        return {'validated_plan': False}
    if expected.get('clarify'):
        return {'asks_clarification': bool(plan.clarification),
                'clarification_mentions_issue': has_terms(plan.clarification, expected['clarify_terms'])}
    actual_foods = Counter((re.sub(r'[（(]生[）)]$', '', item.name.strip()), item.grams)
                           for item in plan.foods)
    checks = {
        'no_unnecessary_clarification': not bool(plan.clarification),
        'meal_route': bool(plan.meal_query) == ('meal' in expected),
        'recipe_route': bool(plan.recipe_query) == ('recipe' in expected),
        'food_bindings': actual_foods == Counter(tuple(item) for item in expected.get('foods', [])),
        'sum_intent': plan.sum_foods == expected.get('sum_foods', False),
        'no_extra_profile_or_weight_route': not (plan.profile or plan.weight),
    }
    if 'meal' in expected:
        label = expected['meal']
        target = str(today - timedelta(days=label['offset']))
        try:
            period = resolve_period(plan.meal_query, today) if plan.meal_query else {}
        except ValueError:
            period = {}
        checks['meal_date_and_type'] = period == {
            'start_date': target, 'end_date': target, 'meal_types': label['meal_types']}
        checks['meal_metric'] = has_terms(plan.meal_query, label.get('terms', []))
    if 'recipe' in expected:
        checks['recipe_rewrite_preserves_intent'] = has_terms(plan.recipe_query, expected['recipe'])
        checks['recipe_drops_old_topic'] = not any(
            term in (plan.recipe_query or '') for term in expected.get('exclude_recipe', []))
    return checks


def evaluate(output):
    if output.exists():
        raise FileExistsError('输出目录已存在，请使用新目录')
    cases = json.loads(Path(__file__).with_name('query_plan_colloquial_cases.json').read_text(encoding='utf-8'))
    model = RecordedModel(create_rewrite_model(max_tokens=1024))
    output.mkdir(parents=True)
    rows = []
    today = date.today()
    for case in cases:
        started = time.perf_counter()
        plan = analyze_question(case['question'], case['history'], model)
        checks = plan_checks(plan, case['expected'], today)
        row = {**case, 'plan': plan.model_dump() if plan is not None else None,
               'raw_plan': model.raw_plan,
               'checks': checks, 'pass': all(checks.values()),
               'elapsed_ms': (time.perf_counter() - started) * 1000}
        rows.append(row)
        print(case['id'], 'PASS' if row['pass'] else 'REVIEW', flush=True)
    passed = sum(row['pass'] for row in rows)
    (output/'report.json').write_text(json.dumps({'date':str(today),'passed':passed,'rows':rows},
                                               ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# 口语查询计划专项', '', f'通过 {passed}/{len(rows)}。只调用前置分析模型。',
             '这是字段检查，追问和改写的具体语义仍需查看原文。', '']
    for row in rows:
        lines.extend([f"## {row['id']} {'PASS' if row['pass'] else 'REVIEW'}",
                      '', row['question'], '', f"检查：{row['checks']}", '',
                      json.dumps(row['plan'], ensure_ascii=False), ''])
        if row['plan'] is None and row['raw_plan'] is not None:
            lines.extend(['模型原始输出', '', str(row['raw_plan']), ''])
    (output/'summary.md').write_text('\n'.join(lines), encoding='utf-8')
    print('REPORT', output, flush=True)


if __name__ == '__main__':
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path(__file__).parent/'outputs'/
                        ('query_plan_colloquial_' + datetime.now().strftime('%Y%m%d_%H%M%S')))
    evaluate(parser.parse_args().output)
