"""Append sourced foods and isolated synthetic users; reruns do not duplicate records."""
import argparse
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path
import secrets
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from database.connection import get_connection
from dao.user_dao import hash_password

BACKEND = Path(__file__).resolve().parents[1]
DATA = BACKEND/'data/nutrition_reference.json'


def seed(today=None):
    today = today or date.today()
    data = json.loads(DATA.read_text(encoding='utf-8'))
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    inserted = []
    try:
        cursor.execute((BACKEND/'database/nutrition_sources.sql').read_text(encoding='utf-8'))
        connection.commit()
        cursor.execute("SELECT GET_LOCK('smart_diet_reference_seed_v1', 10) AS acquired")
        if cursor.fetchone()['acquired'] != 1:
            raise RuntimeError('另一个营养导入正在执行')
        connection.commit()
        connection.start_transaction()
        for row in data['rows']:
            name, category, source_food, portion, *values = row
            cursor.execute('SELECT id FROM foods WHERE name=%s', (name,))
            existing = cursor.fetchone()
            if existing:
                cursor.execute('SELECT dataset FROM food_nutrition_sources WHERE food_id=%s', (existing['id'],))
                provenance = cursor.fetchone()
                if not provenance or provenance['dataset'] != data['dataset']:
                    raise ValueError(f'同名食物已有其他来源，未覆盖：{name}')
                continue
            cursor.execute('SELECT id FROM food_categories WHERE name=%s', (category,))
            category_id = cursor.fetchone()['id']
            cursor.execute('INSERT INTO foods(name,category_id,default_portion_g) VALUES(%s,%s,100)', (name, category_id))
            food_id = cursor.lastrowid
            for key, value in zip(data['columns'][4:], values):
                per100 = (Decimal(str(value))*100/Decimal(str(portion))).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
                cursor.execute('INSERT INTO food_nutrition VALUES(%s,%s,%s)', (food_id,key,per100))
            url = data['fruit_url'] if category == '水果' else data['vegetable_url']
            cursor.execute('INSERT INTO food_nutrition_sources VALUES(%s,%s,%s,%s,%s,%s,%s)',
                           (food_id,data['dataset'],url,source_food,portion,
                            json.dumps(dict(zip(data['columns'][4:],values))),
                            'FDA生鲜可食部分海报，按原份量换算为每100g；原始标示已舍入，零值不代表分析意义上的绝对零。'))
            inserted.append(food_id)
        users = {}
        for username in ['rag_eval_demo','rag_eval_empty']:
            cursor.execute('SELECT user_id FROM users WHERE username=%s', (username,))
            existing = cursor.fetchone()
            if existing:
                user_id = existing['user_id']
            else:
                cursor.execute('INSERT INTO users(username,password_hash,nickname) VALUES(%s,%s,%s)',
                               (username,hash_password(secrets.token_urlsafe(24)),'RAG模拟测试用户'))
                user_id = cursor.lastrowid
                cursor.execute("INSERT INTO health_profile(user_id,target_calorie,allergens) VALUES(%s,1800,'花生')", (user_id,))
            users[username] = user_id
        meals = [(0,'早餐','牛油果（生）',60,8),(0,'午餐','草莓（生）',150,12),
                 (0,'午餐','蘑菇（生）',100,12),(0,'晚餐','梨（生）',166,18),
                 (1,'早餐','猕猴桃（生）',148,8),(1,'午餐','芦笋（生）',186,12),
                 (2,'晚餐','菠萝（生）',224,18)]
        # Only the dedicated synthetic account gets new meals; existing user data is untouched.
        for days, meal, food, grams, hour in meals:
            cursor.execute('SELECT id FROM foods WHERE name=%s',(food,))
            food_id = cursor.fetchone()['id']
            eaten_at = datetime.combine(today-timedelta(days=days),time(hour))
            cursor.execute('SELECT id FROM meal_records WHERE user_id=%s AND food_id=%s AND meal_type=%s AND portion_g=%s AND eaten_at=%s',
                           (users['rag_eval_demo'],food_id,meal,grams,eaten_at))
            if not cursor.fetchone():
                cursor.execute('INSERT INTO meal_records(user_id,food_id,meal_type,portion_g,eaten_at) VALUES(%s,%s,%s,%s,%s)',
                               (users['rag_eval_demo'],food_id,meal,grams,eaten_at))
        for days, weight in [(6,70),(3,69.5),(0,69)]:
            cursor.execute('INSERT IGNORE INTO weight_records(user_id,weight_kg,record_date) VALUES(%s,%s,%s)',
                           (users['rag_eval_demo'],weight,today-timedelta(days=days)))
        connection.commit()
        return {'inserted_food_ids':inserted,'test_users':users,'fixture_date':str(today),
                'fixture_note':'所有测试账户档案、体重和饮食均为模拟数据，不构成饮食建议。'}
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.execute("SELECT RELEASE_LOCK('smart_diet_reference_seed_v1')")
        cursor.fetchall()
        cursor.close()
        connection.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true',help='确认追加食物和模拟账户记录')
    args = parser.parse_args()
    if not args.apply:
        parser.error('此脚本会写数据库，请使用 --apply')
    print(json.dumps(seed(),ensure_ascii=True))
