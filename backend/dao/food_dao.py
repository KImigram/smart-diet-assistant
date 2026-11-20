"""食物 DAO：foods + food_categories + food_nutrition"""
from database.connection import execute_query, execute_update


class FoodDAO:
    @staticmethod
    def search(keyword: str, limit: int = 20):
        """按名称模糊搜索食物，返回含分类名和营养的列表"""
        sql = """
            SELECT f.id, f.name, f.category_id, f.default_portion_g, c.name AS category
            FROM foods f
            JOIN food_categories c ON f.category_id = c.id
            WHERE f.name LIKE %s
            LIMIT %s
        """
        return execute_query(sql, (f"%{keyword}%", limit))

    @staticmethod
    def get_by_id(food_id: int):
        sql = """
            SELECT f.id, f.name, f.category_id, f.default_portion_g, c.name AS category
            FROM foods f
            JOIN food_categories c ON f.category_id = c.id
            WHERE f.id = %s
        """
        rows = execute_query(sql, (food_id,))
        if not rows:
            return None
        food = rows[0]
        # 附带营养成分
        food["nutrition"] = FoodDAO.get_nutrition(food_id)
        food["calorie"] = food["nutrition"].get("calorie")
        food["protein"] = food["nutrition"].get("protein")
        return food

    @staticmethod
    def get_by_name(name: str):
        """按名称精确查找食物，附带营养信息"""
        sql = """
            SELECT f.id, f.name, f.category_id, f.default_portion_g, c.name AS category
            FROM foods f
            JOIN food_categories c ON f.category_id = c.id
            WHERE f.name = %s
            LIMIT 1
        """
        rows = execute_query(sql, (name,))
        if not rows:
            return None
        food = rows[0]
        food["nutrition"] = FoodDAO.get_nutrition(food["id"])
        food["calorie"] = food["nutrition"].get("calorie")
        food["protein"] = food["nutrition"].get("protein")
        return food

    @staticmethod
    def get_nutrition(food_id: int):
        """获取食物营养成分，返回 {nutrient: value_per_100g}"""
        sql = "SELECT nutrient, value_per_100g FROM food_nutrition WHERE food_id = %s"
        rows = execute_query(sql, (food_id,))
        return {r["nutrient"]: float(r["value_per_100g"]) for r in rows}

    @staticmethod
    def list_categories():
        return execute_query("SELECT id, name FROM food_categories ORDER BY id")

    @staticmethod
    def add_category(name: str):
        return execute_update(
            "INSERT IGNORE INTO food_categories (name) VALUES (%s)", (name,)
        )

    @staticmethod
    def add_food(name: str, category_id: int, default_portion_g: float = 100.0):
        return execute_update(
            "INSERT INTO foods (name, category_id, default_portion_g) VALUES (%s, %s, %s)",
            (name, category_id, default_portion_g),
        )

    @staticmethod
    def set_nutrition(food_id: int, nutrient: str, value: float):
        return execute_update(
            """INSERT INTO food_nutrition (food_id, nutrient, value_per_100g)
               VALUES (%s, %s, %s)
               ON DUPLICATE KEY UPDATE value_per_100g = %s""",
            (food_id, nutrient, value, value),
        )
