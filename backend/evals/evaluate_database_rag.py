"""Real MySQL + recipe retrieval + cloud answer evaluation with synthetic users."""
import argparse
from datetime import date, timedelta, datetime
from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path
import re
import sys
import time
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from database.connection import execute_query
from evals.benchmark import compile_labels
from rag.pipeline import answer
from services.rag_service import RAGService


def number(value):
    return float(Decimal(str(value)).quantize(Decimal('.1'),rounding=ROUND_HALF_UP))


def meal_oracle(user_id, case, today):
    end=today-timedelta(days=case.get('offset',0))
    start=end-timedelta(days=case.get('days',1)-1)
    sql='''SELECT m.portion_g,n.nutrient,n.value_per_100g
           FROM meal_records m JOIN food_nutrition n ON n.food_id=m.food_id
           WHERE m.user_id=%s AND DATE(m.eaten_at) BETWEEN %s AND %s'''
    params=[user_id,str(start),str(end)]
    if case.get('meal'):
        sql+=' AND m.meal_type=%s'
        params.append(case['meal'])
    totals={key:Decimal(0) for key in case.get('metrics',['calorie'])}
    for row in execute_query(sql,params):
        if row['nutrient'] in totals:
            totals[row['nutrient']]+=Decimal(str(number(row['portion_g']*row['value_per_100g']/100)))
    return {key:float(value) for key,value in totals.items()}


def food_oracle(name, grams, metrics):
    rows=execute_query('''SELECT n.nutrient,n.value_per_100g FROM foods f
                          JOIN food_nutrition n ON n.food_id=f.id WHERE f.name=%s''',(name,))
    return {row['nutrient']:number(row['value_per_100g']*Decimal(str(grams))/100)
            for row in rows if row['nutrient'] in metrics}


UNIT_PATTERNS = {
    'kcal': r'kcal|千卡|大卡', 'g': r'克|g\b', 'ml': r'毫升|ml\b',
    'min': r'分钟|min\b', 's': r'秒(?:钟)?|s\b', 'C': r'摄氏度|°\s*C|℃|度',
}


def contains_amount(body, expected, unit):
    pattern = rf'(?<![\d.])(\d+(?:\.\d+)?)\s*(?:{UNIT_PATTERNS[unit]})'
    return any(abs(float(match[1])-expected) <= .15
               for match in re.finditer(pattern, body, re.IGNORECASE))


def joint_checks(case, body, context, gold_groups):
    recipes = context.get('recipe', [])
    used = set(re.findall(r'\[(R\d+)\]', body))
    available_ids = {recipe['chunk_id'] for recipe in recipes}
    cited_ids = {recipe['chunk_id'] for recipe in recipes if recipe['citation'] in used}
    checks = {
        'recipe_evidence_retrieved': all(group & available_ids for group in gold_groups),
        'recipe_evidence_cited': all(group & cited_ids for group in gold_groups),
        'recipe_citations_exist': used <= {recipe['citation'] for recipe in recipes},
        'recipe_amounts_with_units': all(contains_amount(body, value, unit)
                                         for value, unit in case['recipe_numbers']),
    }
    if case['kind'] == 'food':
        checks['database_food_portion'] = any(
            food['name'] == case['food'] and food.get('requested_portion_g') == case['grams']
            and all(food.get('requested_nutrition', {}).get(key) == value
                    for key, value in food_oracle(case['food'], case['grams'], case['metrics']).items())
            for food in context.get('food_knowledge', []))
    if case.get('sum_foods'):
        expected_portions = sorted((name, grams) for name, grams in case['foods'])
        actual_portions = sorted(((food['name'], food.get('requested_portion_g'))
                                  for food in context.get('food_knowledge', [])), key=lambda item: item[0])
        checks['database_food_portions'] = actual_portions == expected_portions
        totals = context.get('food_portion_totals', {})
        for key in case['metrics']:
            values = [food_oracle(name, grams, [key]).get(key) for name, grams in case['foods']]
            checks[f'database_food_total_{key}'] = (
                all(value is not None for value in values) and totals.get(key) == number(sum(values)))
    return checks


def evaluate(output, suite='general', split='dev'):
    if output.exists():
        raise FileExistsError('输出目录已存在，请使用新目录')
    users={row['username']:row['user_id'] for row in execute_query(
        "SELECT user_id,username FROM users WHERE username IN ('rag_eval_demo','rag_eval_empty')")}
    if len(users)!=2:
        raise RuntimeError('请先运行 seed_nutrition_reference.py --apply')
    filename = {
        'general': 'database_rag_cases.json',
        'joint': 'database_recipe_cases_v2.json',
        'joint-v1': 'database_recipe_cases.json',
        'joint-expanded': 'database_recipe_cases_v3.json',
    }[suite]
    is_joint = suite != 'general'
    cases=json.loads(Path(__file__).with_name(filename).read_text(encoding='utf-8'))
    if suite == 'joint-expanded':
        cases = [case for case in cases if case['split'] == split]
    today=date.today()
    labels = {}
    if is_joint:
        from rag.chunker import split_recipe_documents
        from rag.document_loader import load_recipe_documents
        labels = compile_labels(cases, split_recipe_documents(load_recipe_documents()))
        fixture_date = execute_query(
            'SELECT MAX(DATE(eaten_at)) AS fixture_date FROM meal_records WHERE user_id=%s',
            (users['rag_eval_demo'],))[0]['fixture_date']
        if not fixture_date:
            raise RuntimeError('模拟账户没有饮食记录，请准备测试数据')
        today = fixture_date
    output.mkdir(parents=True)
    rows=[]
    retrieve=RAGService.retrieve
    for index,case in enumerate(cases,1):
        user_id=users['rag_eval_empty' if case.get('user')=='empty' else 'rag_eval_demo']
        fields = {'yesterday': str(today-timedelta(days=1)),
                  'date': str(today-timedelta(days=case.get('offset',0)))}
        question = case['question'].format(**fields)
        history = [{**message, 'content': message['content'].format(**fields)}
                   for message in case.get('history', [])]
        expected=case.get('expected_numbers',[])
        if case['kind']=='meals':
            expected=list(meal_oracle(user_id,case,today).values())
        elif case['kind']=='food':
            expected=list(food_oracle(case['food'],case['grams'],case['metrics']).values())
        elif case['kind']=='two_foods':
            if case.get('sum_foods'):
                expected = [number(sum(food_oracle(name, grams, [key])[key]
                                       for name, grams in case['foods'])) for key in case['metrics']]
            else:
                expected=[value for name,grams in case['foods'] for value in food_oracle(name,grams,case['metrics']).values()]
        elif case['kind']=='remaining':
            target=execute_query('SELECT target_calorie FROM health_profile WHERE user_id=%s',(user_id,))[0]['target_calorie']
            expected=[number(max(0,target-Decimal(str(meal_oracle(user_id,{},today)['calorie']))))]
        captured=[]
        captured_plan=[]
        def capture(uid,query,**kwargs):
            plan = kwargs.get('plan')
            captured_plan.append(plan.model_dump() if plan is not None else None)
            context=retrieve(uid,query,**kwargs)
            captured.append(context)
            return context
        started=time.perf_counter()
        error=None
        reply=''
        try:
            with patch.object(RAGService,'retrieve',side_effect=capture):
                reply=answer(user_id,question,history)
        except Exception as exc:
            error=type(exc).__name__
        context=captured[-1] if captured else {}
        body=reply.split('检索参考资料')[0].replace('**','').replace(',','')
        numbers=[float(value) for value in re.findall(r'(?<![\d.])\d+(?:\.\d+)?',body)]
        checks={'request_succeeded':error is None and bool(reply),
                'answer_numbers':all(any(abs(value-found)<=.15 for found in numbers) for value in expected),
                'answer_terms':all(any(term in body for term in alternatives) for alternatives in case.get('term_groups',[]))}
        if not context.get('recipe'):
            checks['no_fabricated_recipe_citation'] = re.search(r'\[R\d+\]',body) is None
        request=context.get('nutrition_request',{})
        if case['kind']=='meals':
            end=today-timedelta(days=case.get('offset',0))
            start=end-timedelta(days=case.get('days',1)-1)
            gold=meal_oracle(user_id,case,today)
            checks['context_period']=request.get('start_date')==str(start) and request.get('end_date')==str(end)
            checks['context_meal']=request.get('meal_types')==([case['meal']] if case.get('meal') else [])
            checks['context_totals']=all(request.get('totals',{}).get(key) is not None and abs(float(request['totals'][key])-value)<.01 for key,value in gold.items())
        if case['kind']=='no_records':
            checks['context_no_records']=request.get('status')=='no_records'
        if case['kind']=='clarify':
            checks['context_clarify']=request.get('status')=='needs_clarification'
        if case.get('recipe_source'):
            checks['recipe_citation']='[R' in body
            checks['recipe_retrieved']=any(case['recipe_source'].removesuffix('.md').split('/')[-1]==recipe['title'] for recipe in context.get('recipe',[]))
        if is_joint:
            if case['kind'] == 'meals' and not any(expected):
                raise RuntimeError(f"{case['id']}: 测试日期或餐次缺少有效模拟记录")
            units = {'calorie':'kcal', 'protein':'g'}
            checks['database_amounts_with_units'] = all(
                contains_amount(body, value, units[key])
                for key, value in zip(case.get('metrics', []), expected))
            checks.update(joint_checks(case, body, context, labels[case['id']]['groups']))
        row={'id':case['id'],'question':question,'kind':case['kind'],'history':history,
             'plan':captured_plan[-1] if captured_plan else None,
             'expected_numbers':expected,'checks':checks,'screen_pass':all(checks.values()),
             'answer':reply,'context':context,'error':error,'elapsed_ms':(time.perf_counter()-started)*1000}
        rows.append(row)
        (output/'report.json').write_text(json.dumps({'date':str(today),'suite':suite,'split':split if suite=='joint-expanded' else None,'questions_file':filename,'rows':rows},ensure_ascii=False,default=str,indent=2),encoding='utf-8')
        print(f"[{index}/{len(cases)}] {case['id']} {'PASS' if row['screen_pass'] else 'REVIEW'}",flush=True)
    passed=sum(row['screen_pass'] for row in rows)
    lines=['# 数据库联动 RAG 实测','',f'模拟用户，{len(rows)} 题。自动初筛通过 {passed} 题，需复核 {len(rows)-passed} 题。',
           '', '数值出现与关键词匹配仅用于自动初筛，不能证明语义、单位、引用和全部计算都正确。下方保留完整回答供人工复核。','']
    for row in rows:
        lines.extend([f"## {row['id']} {'PASS' if row['screen_pass'] else 'REVIEW'}",'',row['question'],'',
                      f"期望数值 {row['expected_numbers']}，检查 {row['checks']}",'',row['answer'],''])
    (output/'summary.md').write_text('\n'.join(lines),encoding='utf-8')
    print('REPORT',output,flush=True)


if __name__=='__main__':
    if sys.platform=='win32':sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', choices=['general', 'joint', 'joint-v1', 'joint-expanded'], default='general')
    parser.add_argument('--split', choices=['dev', 'holdout'], default='dev', help='仅用于 joint-expanded')
    parser.add_argument('--output',type=Path,default=Path(__file__).parent/'outputs'/('database_rag_'+datetime.now().strftime('%Y%m%d_%H%M%S')))
    args = parser.parse_args()
    evaluate(args.output, args.suite, args.split)
