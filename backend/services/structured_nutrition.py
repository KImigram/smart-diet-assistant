"""Resolve bounded date/meal requests and compute database nutrition in Python."""
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import re

from database.connection import execute_query
from dao.food_dao import FoodDAO
from dao.meal_dao import MealDAO

NUTRIENTS = ('calorie','protein','fat','carb','fiber','sodium')
UNITS = {'calorie':'kcal','protein':'g','fat':'g','carb':'g','fiber':'g','sodium':'mg'}
GRAMS = re.compile(r'(\d+(?:\.\d+)?)\s*(千克|公斤|kg|克|g)', re.IGNORECASE)
MEAL_ALIASES = {
    '早餐': ('早餐', '早饭'),
    '午餐': ('午餐', '午饭', '中饭', '中餐'),
    '晚餐': ('晚餐', '晚饭'),
    '加餐': ('加餐',),
}


def portion_values(nutrition, grams):
    ratio = Decimal(str(grams))/100
    return {key: float((Decimal(str(nutrition[key]))*ratio).quantize(Decimal('.1'), rounding=ROUND_HALF_UP))
            if key in nutrition else None for key in NUTRIENTS}


def resolve_period(question, today=None):
    today = today or date.today()
    question = re.sub(r'(?:不要混入|不要包括|不包括|不含|排除|不计入|不算|不要算|别算)(今天|昨天|前天)', '', question)
    start = today-timedelta(days=2)
    end = today
    dates = re.findall(r'\d{4}-\d{2}-\d{2}', question)
    if dates:
        if len(dates)>2:
            raise ValueError('一次最多查询两个日期组成的连续区间')
        start, end = date.fromisoformat(dates[0]), date.fromisoformat(dates[-1])
    elif '上周' in question:
        end = today-timedelta(days=today.weekday()+1)
        start = end-timedelta(days=6)
    elif '本周' in question:
        start = today-timedelta(days=today.weekday())
    elif '今天' in question and '昨天' in question and any(word in question for word in ['和','与','比较','对比','分别','两天','比昨天']):
        start = today-timedelta(days=1)
    elif '前天' in question:
        start = end = today-timedelta(days=2)
    elif '昨天' in question:
        start = end = today-timedelta(days=1)
    elif '今天' in question or '今日' in question:
        start = end = today
    elif '近一周' in question or '最近一周' in question:
        start = today-timedelta(days=6)
    elif match := re.search(r'(?:最近|近)(\d+)天',question):
        start = today-timedelta(days=int(match[1])-1)
    elif any(word in question for word in ['上个月','本月','去年','上月']):
        raise ValueError('请提供明确的起止日期，范围不超过31天')
    if not 0 <= (end-start).days < 31:
        raise ValueError('日期范围需为1至31天，且起始日期不得晚于结束日期')
    meals = [meal for meal, aliases in MEAL_ALIASES.items()
             if any(alias in question for alias in aliases)]
    return {'start_date':str(start),'end_date':str(end),'meal_types':meals}


def matching_foods(question):
    foods = execute_query('SELECT f.id,f.name,c.name AS category FROM foods f JOIN food_categories c ON c.id=f.category_id')
    candidates = []
    aliases = {'番茄': ['西红柿'], '番茄炒蛋':['西红柿炒鸡蛋']}
    for food in foods:
        stem = re.sub(r'[（(].*?[）)]','',food['name'])
        for alias in {food['name'],stem,*aliases.get(food['name'],[])}:
            for match in re.finditer(re.escape(alias), question):
                candidates.append((len(alias),match.start(),match.end(),food))
    chosen = []
    for length,start,end,food in sorted(candidates,key=lambda row:(-row[0],row[1],row[3]['id'])):
        if any(start<e and end>s for s,e,_ in chosen):
            continue
        chosen.append((start,end,food))
    return sorted(chosen,key=lambda row:row[0])


def nutrition_reference(food, citation, grams=None):
    nutrition = FoodDAO.get_nutrition(food['id'])
    sources = execute_query('SELECT dataset,source_url,source_food,source_portion_g,note FROM food_nutrition_sources WHERE food_id=%s',(food['id'],))
    item = {'citation':citation,'name':food['name'],'category':food['category'],
            'nutrition_per_100g':nutrition,'units':UNITS,
            'provenance':sources[0] if sources else {'note':'原有演示数据，未核实来源；只作数据库参考估算。'}}
    if grams is not None:
        item['requested_portion_g'] = float(grams)
        item['requested_nutrition'] = portion_values(nutrition,grams)
    return item


def planned_food_knowledge(requests):
    result = []
    for request in requests:
        name = request.name.strip()
        label = FoodDAO.get_by_name(name)
        if label is None:
            candidates = [food for _, _, food in matching_foods(name)
                          if re.sub(r'[（(].*?[）)]','',food['name']) == name]
            if len(candidates) != 1:
                return None
            label = candidates[0]
        result.append(nutrition_reference(label, f'D{len(result)+1}', request.grams))
    return result


def food_knowledge(question):
    matches = matching_foods(question)
    portions = {}
    for quantity in GRAMS.finditer(question):
        distances = [(max(start-quantity.end(),quantity.start()-end,0),i)
                     for i,(start,end,_) in enumerate(matches)]
        if distances:
            distance,index = min(distances)
            if distance <= 6:
                food_id = matches[index][2]['id']
                portions.setdefault(food_id,[]).append(quantity)
    result = []
    seen = set()
    for _, _, food in matches:
        if food['id'] in seen:
            continue
        seen.add(food['id'])
        grams = None
        candidates = portions.get(food['id'],[])
        portion = candidates[0] if len(candidates)==1 else None
        if portion:
            quantity = Decimal(portion[1])*(1000 if portion[2].lower() in {'kg','千克','公斤'} else 1)
            if 0 < quantity <= 10000:
                grams = quantity
        result.append(nutrition_reference(food, f'D{len(result)+1}', grams))
    return result


def meal_context(user_id, question, today=None):
    today = today or date.today()
    try:
        period = resolve_period(question,today)
    except ValueError as exc:
        return {'status':'needs_clarification','reason':str(exc),'today':str(today),'records':[]}
    rows = MealDAO.list_by_date_range(user_id,period['start_date'],period['end_date'])
    if period['meal_types']:
        rows = [row for row in rows if row['meal_type'] in period['meal_types']]
    records = []
    for row in rows:
        nutrition = portion_values(FoodDAO.get_nutrition(row['food_id']),row['portion_g'])
        stamp = row['eaten_at']
        records.append({'date':str(stamp)[:10],'meal_type':row['meal_type'],'food_name':row['food_name'],
                        'portion_g':float(row['portion_g']),**nutrition})
    def totals(items):
        return {key: round(sum(Decimal(str(item[key])) for item in items),1)
                if items and all(item[key] is not None for item in items) else None for key in NUTRIENTS}
    daily = []
    current = date.fromisoformat(period['start_date'])
    while current <= date.fromisoformat(period['end_date']):
        items = [row for row in records if row['date']==str(current)]
        daily.append({'date':str(current),'record_count':len(items),'totals':totals(items)})
        current += timedelta(days=1)
    return {'status':'ok' if records else 'no_records','today':str(today),**period,
            'record_count':len(records),'records':records,'totals':totals(records),
            'daily_totals':daily,'units':UNITS,
            'note':'程序按实际克重换算并汇总；无记录不等于当天实际摄入为0，缺失营养值为null。'}
