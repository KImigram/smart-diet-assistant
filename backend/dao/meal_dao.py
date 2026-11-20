"""饮食记录 DAO：meal_records"""
from database.connection import execute_query, execute_update


class MealDAO:
    @staticmethod
    def add(user_id: int, food_id: int, meal_type: str, portion_g: float, eaten_at: str):
        return execute_update(
            """INSERT INTO meal_records (user_id, food_id, meal_type, portion_g, eaten_at)
               VALUES (%s, %s, %s, %s, %s)""",
            (user_id, food_id, meal_type, portion_g, eaten_at),
        )

    @staticmethod
    def delete(record_id: int):
        return execute_update("DELETE FROM meal_records WHERE id = %s", (record_id,))

    @staticmethod
    def update_portion(record_id: int, portion_g: float):
        return execute_update(
            "UPDATE meal_records SET portion_g = %s WHERE id = %s",
            (portion_g, record_id),
        )

    @staticmethod
    def list_by_date(user_id: int, date_str: str):
        """查询某天的饮食记录，JOIN 食物名和分类"""
        sql = """
            SELECT m.id, m.food_id, m.meal_type, m.portion_g, m.eaten_at,
                   f.name AS food_name, c.name AS category
            FROM meal_records m
            JOIN foods f ON m.food_id = f.id
            JOIN food_categories c ON f.category_id = c.id
            WHERE m.user_id = %s AND DATE(m.eaten_at) = %s
            ORDER BY m.eaten_at
        """
        return execute_query(sql, (user_id, date_str))

    @staticmethod
    def list_by_date_range(user_id: int, start_date: str, end_date: str):
        sql = """
            SELECT m.id, m.food_id, m.meal_type, m.portion_g, m.eaten_at,
                   f.name AS food_name
            FROM meal_records m
            JOIN foods f ON m.food_id = f.id
            WHERE m.user_id = %s AND DATE(m.eaten_at) BETWEEN %s AND %s
            ORDER BY m.eaten_at
        """
        return execute_query(sql, (user_id, start_date, end_date))

    @staticmethod
    def daily_summary(user_id: int, date_str: str):
        """按餐次聚合当日热量（需要 JOIN food_nutrition）"""
        sql = """
            SELECT m.meal_type,
                   SUM(m.portion_g / 100 * fn.value_per_100g) AS calorie
            FROM meal_records m
            JOIN food_nutrition fn ON m.food_id = fn.food_id AND fn.nutrient = 'calorie'
            WHERE m.user_id = %s AND DATE(m.eaten_at) = %s
            GROUP BY m.meal_type
        """
        return execute_query(sql, (user_id, date_str))
