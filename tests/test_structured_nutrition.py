"""Date selection, missing values and portions without a database or model."""
from datetime import date
from pathlib import Path
import sys
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from services.structured_nutrition import resolve_period, portion_values, meal_context, food_knowledge
from services import structured_nutrition as module


def test_dates_and_meal_types_are_exact():
    today = date(2026,11,18)
    assert resolve_period('昨天午餐',today) == {'start_date':'2026-11-17','end_date':'2026-11-17','meal_types':['午餐']}
    assert resolve_period('昨天午饭多少大卡？晚上想喝紫菜蛋花汤。', today)['meal_types'] == ['午餐']
    assert resolve_period('昨天总热量，不要混入今天',today)['end_date']=='2026-11-17'
    assert resolve_period('今天和昨天分别登记多少',today)['start_date']=='2026-11-17'
    assert resolve_period('2026-09-18到2026-09-20',today)['start_date']=='2026-09-18'
    assert resolve_period('最近7天',today)['start_date']=='2026-11-12'
    assert resolve_period('上周',today)['end_date']=='2026-11-15'
    with pytest.raises(ValueError): resolve_period('最近0天',today)
    with pytest.raises(ValueError): resolve_period('最近99天',today)
    with pytest.raises(ValueError): resolve_period('上个月',today)


def test_portions_do_not_convert_missing_nutrition_to_zero():
    actual = portion_values({'calorie':166.67,'protein':3.33},60)
    assert actual['calorie']==100 and actual['protein']==2
    assert actual['sodium'] is None


def test_empty_meal_history_is_unknown_not_zero(monkeypatch):
    monkeypatch.setattr(module.MealDAO,'list_by_date_range',lambda *args:[])
    actual = meal_context(1,'今天午餐',date(2026,11,18))
    assert actual['status']=='no_records'
    assert actual['totals']['calorie'] is None


def test_debug_context_handles_unknown_nutrients():
    from services.rag_service import RAGService
    result = RAGService._format_context({'recent_meals':[{
        'date':'2026-11-18','meal_type':'午餐','food_name':'未标注食物',
        'portion_g':100,'calorie':None,'protein':None}]})
    assert '汇总：热量未知' in result


def test_chat_runs_both_sources_for_colloquial_nutrition_and_recipe(monkeypatch):
    from rag import runtime
    from services.rag_service import RAGService

    question = '60克牛油果多少大卡？美式炒蛋的蛋液要静置多久？'
    calls = []
    monkeypatch.setattr(RAGService, '_retrieve_profile', lambda _: {})
    monkeypatch.setattr(module, 'meal_context', lambda *_: {'status':'no_records','records':[]})
    monkeypatch.setattr(RAGService, '_retrieve_food_knowledge',
                        lambda query: calls.append(('food', query)) or [{'name':'牛油果'}])
    monkeypatch.setattr(runtime, 'recipe_context',
                        lambda query: calls.append(('recipe', query)) or [{'title':'美式炒蛋'}])
    context = RAGService.retrieve(1, question)
    assert calls == [('food', question), ('recipe', question)]
    assert context['food_knowledge'] and context['recipe']

    calls.clear()
    pure_question = '60克牛油果多少大卡？'
    context = RAGService.retrieve(1, pure_question)
    assert calls == [('food', pure_question)]
    assert context['recipe'] == []


@pytest.mark.parametrize(('question', 'should_search'), [
    ('我今天登记了多少热量？', False),
    ('我昨天午饭吃了多少蛋白质？', False),
    ('我今天登记了多少大卡？我档案里的目标热量是多少？', False),
    ('我今天登记了多少热量？我可以加点什么？', True),
    ('我一天摄入多少大卡，紫菜下锅前泡多久？', True),
    ('我今天的饮食记录加上蛋炒饭怎么做？', True),
    ('45分钟够吗？', True),
])
def test_recipe_route_only_skips_known_structured_questions(question, should_search):
    from services.rag_service import RAGService

    assert RAGService.needs_recipe_search(question) is should_search


def test_food_matching_prefers_long_name_and_supports_before_after_portions(monkeypatch):
    foods=[{'id':1,'name':'桃（生）','category':'水果'},
           {'id':2,'name':'油桃（生）','category':'水果'},
           {'id':3,'name':'草莓（生）','category':'水果'}]
    monkeypatch.setattr(module,'execute_query',lambda sql,params=None: foods if 'FROM foods' in sql else [])
    monkeypatch.setattr(module.FoodDAO,'get_nutrition',lambda fid:{'calorie':40})
    result = food_knowledge('油桃60克和150克草莓有多少热量？')
    assert [row['name'] for row in result]==['油桃（生）','草莓（生）']
    assert [row['requested_portion_g'] for row in result]==[60,150]
    assert [row['requested_nutrition']['calorie'] for row in result]==[24,60]
    result = food_knowledge('60克油桃和150克草莓有多少热量？')
    assert [row['requested_portion_g'] for row in result]==[60,150]
    result = food_knowledge('下午想吃点草莓，再烤个巴斯克。150克草莓多少大卡？')
    assert len(result)==1 and result[0]['requested_portion_g']==150
    result = food_knowledge('半斤草莓热量多少？')
    assert result[0]['requested_portion_g'] == 250
    assert result[0]['requested_nutrition']['calorie'] == 100


@pytest.mark.parametrize('text,expected', [
    ('半斤', '250'), ('两斤', '1000'), ('三两', '150'), ('2两', '100'),
    ('0.5 公斤', '500'), ('0.25千克', '250'), ('.5 KG', '500'),
    ('150g草莓', '150'), ('150毫克', '0.15'), ('150mg', '0.15'),
    ('1磅', '453.59237'), ('2lbs', '907.18474'), ('1oz', '28.349523125'),
    ('1盎司', '28.349523125'),
])
def test_portion_weights_convert_to_grams(text, expected):
    from decimal import Decimal
    from services.portion_units import PORTION_WEIGHT, weight_in_grams

    match = PORTION_WEIGHT.search(text)
    assert match is not None
    assert weight_in_grams(match) == Decimal(expected)


@pytest.mark.parametrize('text', ['150ml', '150GB', '2kgf', '10克拉', '-30g', '一两次', '二十斤'])
def test_portion_weights_do_not_match_unrelated_or_partial_units(text):
    from services.portion_units import PORTION_WEIGHT

    assert PORTION_WEIGHT.search(text) is None
