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
