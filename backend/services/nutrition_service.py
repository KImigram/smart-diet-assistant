"""营养计算引擎：根据食物和份量计算实际营养摄入"""
from dao.food_dao import FoodDAO

# 每克营养素热量 (kcal/g)
KCAL_PER_GRAM = {"protein": 4.0, "fat": 9.0, "carb": 4.0}


class NutritionService:
    @staticmethod
    def calc(food_id: int, portion_g: float) -> dict:
        """
        计算指定份量的营养摄入。
        返回 {calorie, protein, fat, carb, fiber, sodium} 实际摄入量
        """
        nutrition = FoodDAO.get_nutrition(food_id)
        ratio = float(portion_g) / 100.0
        result = {}
        for nutrient in ["calorie", "protein", "fat", "carb", "fiber", "sodium"]:
            result[nutrient] = round(float(nutrition.get(nutrient, 0.0)) * ratio, 1)
        return result

    @staticmethod
    def calc_from_list(items: list[dict]) -> dict:
        """
        批量计算汇总。items: [{food_id, portion_g}]
        返回汇总营养
        """
        total = {k: 0.0 for k in ["calorie", "protein", "fat", "carb", "fiber", "sodium"]}
        for item in items:
            n = NutritionService.calc(item["food_id"], item["portion_g"])
            for k in total:
                total[k] += n.get(k, 0.0)
        return {k: round(v, 1) for k, v in total.items()}

    @staticmethod
    def macro_ratio(protein: float, fat: float, carb: float) -> dict:
        """计算三大营养素供能占比"""
        p_kcal = protein * KCAL_PER_GRAM["protein"]
        f_kcal = fat * KCAL_PER_GRAM["fat"]
        c_kcal = carb * KCAL_PER_GRAM["carb"]
        total = p_kcal + f_kcal + c_kcal
        if total <= 0:
            return {"protein": 0.0, "fat": 0.0, "carb": 0.0}
        return {
            "protein": round(p_kcal / total * 100, 1),
            "fat": round(f_kcal / total * 100, 1),
            "carb": round(c_kcal / total * 100, 1),
        }
