"""统计分析：日/周营养摄入统计、达标率、营养素供能比"""
from datetime import datetime, timedelta
from dao.meal_dao import MealDAO
from dao.user_dao import UserDAO
from services.nutrition_service import NutritionService


class StatsService:
    @staticmethod
    def daily(user_id: int, date_str: str) -> dict:
        """日报告：各餐次热量、营养素汇总、达标率"""
        records = MealDAO.list_by_date(user_id, date_str)
        profile = UserDAO.get_profile(user_id)
        target_cal = profile["target_calorie"] if profile else 2000

        # 按餐次聚合
        by_meal = {}
        total = {"calorie": 0.0, "protein": 0.0, "fat": 0.0, "carb": 0.0}
        for r in records:
            n = NutritionService.calc(r["food_id"], r["portion_g"])
            meal = r["meal_type"]
            if meal not in by_meal:
                by_meal[meal] = 0.0
            by_meal[meal] += n["calorie"]
            for k in total:
                total[k] += n.get(k, 0.0)

        # 达标率
        achievement = {
            "calorie": round(total["calorie"] / target_cal * 100, 1) if target_cal else 0,
        }
        # 营养素目标（按热量分配：蛋白15% 脂肪30% 碳水55%）
        targets = {
            "protein": round(target_cal * 0.15 / 4, 1),
            "fat": round(target_cal * 0.30 / 9, 1),
            "carb": round(target_cal * 0.55 / 4, 1),
        }
        for k in ["protein", "fat", "carb"]:
            achievement[k] = round(total[k] / targets[k] * 100, 1) if targets[k] else 0

        # 供能比
        ratio = NutritionService.macro_ratio(total["protein"], total["fat"], total["carb"])

        return {
            "date": date_str,
            "by_meal": by_meal,
            "total": {k: round(v, 1) for k, v in total.items()},
            "targets": {"calorie": target_cal, **targets},
            "achievement": achievement,
            "macro_ratio": ratio,
        }

    @staticmethod
    def weekly(user_id: int, end_date_str: str = None) -> dict:
        """周报告：最近7天每日热量、周均营养、达标率"""
        if end_date_str is None:
            end_date = datetime.now().date()
        else:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        start_date = end_date - timedelta(days=6)

        profile = UserDAO.get_profile(user_id)
        target_cal = profile["target_calorie"] if profile else 2000

        daily_calories = []
        labels = []
        sum_total = {"calorie": 0.0, "protein": 0.0, "fat": 0.0, "carb": 0.0}
        days_count = 0

        for i in range(7):
            d = start_date + timedelta(days=i)
            d_str = d.strftime("%Y-%m-%d")
            day_stats = StatsService.daily(user_id, d_str)
            daily_calories.append(round(day_stats["total"]["calorie"], 1))
            labels.append(d.strftime("%m/%d"))
            for k in sum_total:
                sum_total[k] += day_stats["total"][k]
            if day_stats["total"]["calorie"] > 0:
                days_count += 1

        avg = {k: round(v / max(days_count, 1), 1) for k, v in sum_total.items()}
        ratio = NutritionService.macro_ratio(avg["protein"], avg["fat"], avg["carb"])

        return {
            "labels": labels,
            "daily_calories": daily_calories,
            "average": avg,
            "target_calorie": target_cal,
            "macro_ratio": ratio,
            "days_with_data": days_count,
        }
