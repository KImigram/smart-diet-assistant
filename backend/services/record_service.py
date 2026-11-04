"""饮食记录管理：CRUD + 按日期/餐次查询"""
from datetime import datetime
from dao.meal_dao import MealDAO
from dao.food_dao import FoodDAO
from services.nutrition_service import NutritionService


class RecordService:
    @staticmethod
    def add(user_id: int, food_id: int, meal_type: str,
            portion_g: float, eaten_at: str = None) -> dict:
        """添加一条饮食记录，返回记录+营养"""
        if eaten_at is None:
            eaten_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        record_id = MealDAO.add(user_id, food_id, meal_type, portion_g, eaten_at)
        nutrition = NutritionService.calc(food_id, portion_g)
        food = FoodDAO.get_by_id(food_id)
        return {
            "id": record_id,
            "food_id": food_id,
            "food_name": food["name"] if food else "",
            "meal_type": meal_type,
            "portion_g": portion_g,
            "eaten_at": eaten_at,
            "nutrition": nutrition,
        }

    @staticmethod
    def delete(record_id: int):
        return MealDAO.delete(record_id)

    @staticmethod
    def update_portion(record_id: int, portion_g: float):
        return MealDAO.update_portion(record_id, portion_g)

    @staticmethod
    def list_by_date(user_id: int, date_str: str) -> list[dict]:
        """查询某日记录，每条附带营养"""
        records = MealDAO.list_by_date(user_id, date_str)
        for r in records:
            r["nutrition"] = NutritionService.calc(r["food_id"], r["portion_g"])
        return records

    @staticmethod
    def daily_total(user_id: int, date_str: str) -> dict:
        """当日营养摄入汇总"""
        records = MealDAO.list_by_date(user_id, date_str)
        items = [{"food_id": r["food_id"], "portion_g": r["portion_g"]} for r in records]
        total = NutritionService.calc_from_list(items)
        # 按餐次分组
        by_meal = {}
        for r in records:
            meal = r["meal_type"]
            n = NutritionService.calc(r["food_id"], r["portion_g"])
            if meal not in by_meal:
                by_meal[meal] = {"calorie": 0.0, "protein": 0.0, "fat": 0.0, "carb": 0.0}
            for k in by_meal[meal]:
                by_meal[meal][k] += n.get(k, 0.0)
        return {"total": total, "by_meal": by_meal, "count": len(records)}
