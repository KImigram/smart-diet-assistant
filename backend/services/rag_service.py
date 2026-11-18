"""
结构化 + 向量 混合 RAG 检索服务
从 MySQL 多表检索用户数据 + 从营养知识库向量检索菜谱知识，格式化为上下文，拼接 Prompt

这是 Agent 开发的核心技术：
1. 查询规划 — 根据问题关键词决定检索哪些数据源（结构化表 / 向量知识库）
2. 结果聚合 — 多条记录格式化为结构化文本
3. 上下文工程 — System Prompt + 检索结果 + 历史对话 + 当前问题
"""
from datetime import datetime, timedelta
from dao.user_dao import UserDAO
from dao.meal_dao import MealDAO
from dao.food_dao import FoodDAO
from dao.chat_dao import ChatDAO
from services.nutrition_service import NutritionService


class RAGService:
    """混合 RAG：结构化检索（MySQL）+ 向量检索（营养知识库 Chroma）"""

    # 关键词 → 检索意图映射
    INTENT_KEYWORDS = {
        "profile": ["身高", "体重", "bmi", "档案", "目标", "热量目标", "过敏原", "活动"],
        "recent_meals": ["今天", "昨天", "最近", "吃了", "饮食", "摄入", "记录", "餐"],
        "nutrition": ["营养", "蛋白", "脂肪", "碳水", "热量", "卡路里", "维生素", "纤维"],
        "food_knowledge": ["什么", "怎么", "能吃", "可以", "好不好", "功效", "作用"],
        "weight": ["体重", "减肥", "增重", "胖", "瘦", "减脂", "增肌"],
        "recipe": ["怎么做", "做法", "菜谱", "烹饪", "如何做", "怎么煮", "怎么烧",
                   "怎么炒", "怎么炖", "步骤", "家常", "红烧", "清蒸", "凉拌",
                   "烘焙", "烤箱", "煎", "炸", "煲汤", "食谱"],
    }

    @staticmethod
    def detect_intents(question: str) -> set[str]:
        """根据问题关键词检测需要检索的意图"""
        intents = set()
        q = question.lower()
        for intent, keywords in RAGService.INTENT_KEYWORDS.items():
            for kw in keywords:
                if kw in q:
                    intents.add(intent)
                    break
        # 默认至少检索档案和最近饮食（个性化基础）
        intents.add("profile")
        if not intents & {"recent_meals", "weight"}:
            intents.add("recent_meals")
        return intents

    @staticmethod
    def retrieve(user_id: int, question: str) -> dict:
        """
        检索相关数据，返回结构化上下文字典。
        返回：{profile, recent_meals, food_knowledge, weight, summary}
        """
        intents = RAGService.detect_intents(question)
        context = {}

        # 1. 健康档案（几乎总是需要）
        if "profile" in intents:
            context["profile"] = RAGService._retrieve_profile(user_id)

        # 2. 最近饮食记录
        if "recent_meals" in intents:
            from services.structured_nutrition import meal_context
            context['nutrition_request'] = meal_context(user_id, question)
            context['recent_meals'] = context['nutrition_request']['records']
            request = context['nutrition_request']
            if request['status'] == 'ok' and request['start_date'] == request['end_date'] and not request['meal_types']:
                target = context.get('profile', {}).get('target_calorie')
                calorie = request['totals']['calorie']
                if target is not None and calorie is not None:
                    request['calorie_balance'] = {'target':float(target),
                        'remaining':round(max(0, float(target)-float(calorie)),1),
                        'excess':round(max(0, float(calorie)-float(target)),1)}

        # 3. 食物知识（问题中提到具体食物时）
        if "food_knowledge" in intents or "nutrition" in intents:
            context["food_knowledge"] = RAGService._retrieve_food_knowledge(question)

        # 4. 体重趋势
        if "weight" in intents:
            context["weight"] = RAGService._retrieve_weight(user_id)

        structured_question = any(word in question for word in [
            '今天','昨天','登记','记录','档案','体重','热量','蛋白','脂肪','碳水','纤维','卡路里','营养','维生素'])
        recipe_question = 'recipe' in intents or any(word in question for word in [
            '怎么','如何','为什么','食材','原料','工具','隔夜','配方','过敏','忌口','能吃'])
        if structured_question and not recipe_question:
            context['recipe'] = []
        else:
            from rag.runtime import recipe_context
            context['recipe'] = recipe_context(question)

        return context

    @staticmethod
    def build_prompt(user_id: int, question: str,
                     history_messages: list[dict] = None) -> list[dict]:
        """
        构建发送给大模型的完整消息列表。
        格式：[system, context(用户), history..., current_question]
        """
        from langchain_core.messages import convert_to_openai_messages
        from rag.context_builder import build_messages
        return convert_to_openai_messages(build_messages(
            RAGService.retrieve(user_id, question), question, history_messages
        ))

    # ---- 各数据源检索 ----

    @staticmethod
    def _retrieve_profile(user_id: int) -> dict:
        profile = UserDAO.get_profile(user_id)
        if not profile:
            return {}
        # 计算 BMI
        height = float(profile["height_cm"]) if profile.get("height_cm") else None
        weight_rec = UserDAO.latest_weight(user_id)
        weight = float(weight_rec["weight_kg"]) if weight_rec else None
        bmi = round(weight / ((height / 100) ** 2), 1) if height and height > 0 and weight else None
        return {
            "nickname": profile.get("nickname", ""),
            "gender": profile.get("gender", ""),
            "age": profile.get("age", 0),
            "height_cm": height,
            "weight_kg": weight,
            "bmi": bmi,
            "target_calorie": profile.get("target_calorie", 2000),
            "activity_level": profile.get("activity_level", ""),
            "allergens": profile.get("allergens", ""),
        }

    @staticmethod
    def _retrieve_recent_meals(user_id: int, days: int = 3) -> list[dict]:
        """检索最近 N 天饮食记录，附带营养计算"""
        end = datetime.now().date()
        start = end - timedelta(days=days - 1)
        records = MealDAO.list_by_date_range(
            user_id, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
        )
        result = []
        for r in records:
            nutrition = NutritionService.calc(r["food_id"], float(r["portion_g"]))
            result.append({
                "date": r["eaten_at"][:10] if isinstance(r["eaten_at"], str)
                else r["eaten_at"].strftime("%Y-%m-%d"),
                "meal_type": r["meal_type"],
                "food_name": r["food_name"],
                "portion_g": float(r["portion_g"]),
                "calorie": nutrition["calorie"],
                "protein": nutrition["protein"],
            })
        return result

    @staticmethod
    def _retrieve_food_knowledge(question: str) -> list[dict]:
        """从问题中提取食物名，检索营养知识"""
        from services.structured_nutrition import food_knowledge
        return food_knowledge(question)

    @staticmethod
    def _retrieve_weight(user_id: int, days: int = 30) -> dict:
        records = UserDAO.list_weight(user_id, days)
        if not records:
            return {}
        weights = [float(r["weight_kg"]) for r in records]
        return {
            "current": weights[-1],
            "start": weights[0],
            "change": round(weights[-1] - weights[0], 1),
            "records_count": len(records),
        }

    # ---- 上下文格式化 ----

    @staticmethod
    def _format_context(context: dict) -> str:
        """将检索结果格式化为大模型易读的文本"""
        lines = []

        if "profile" in context and context["profile"]:
            p = context["profile"]
            lines.append(
                f"健康档案：{p['nickname']}，{p['gender']}，{p['age']}岁，"
                f"身高{p['height_cm']}cm，体重{p['weight_kg']}kg，BMI {p['bmi']}，"
                f"目标热量{p['target_calorie']}kcal/天，活动水平{p['activity_level']}"
            )
            if p.get("allergens"):
                lines.append(f"过敏原/忌口：{p['allergens']}")

        if "recent_meals" in context and context["recent_meals"]:
            lines.append(f"\n最近饮食记录（共{len(context['recent_meals'])}条）：")
            for m in context["recent_meals"]:
                lines.append(
                    f"  {m['date']} {m['meal_type']}：{m['food_name']} "
                    f"{m['portion_g']}g → {m['calorie']}kcal，蛋白{m['protein']}g"
                )
            # 汇总
            meals = context['recent_meals']
            total_cal = round(sum(m['calorie'] for m in meals),1) if all(m['calorie'] is not None for m in meals) else '未知'
            total_pro = round(sum(m['protein'] for m in meals),1) if all(m['protein'] is not None for m in meals) else '未知'
            lines.append(f"  汇总：热量{total_cal}kcal，蛋白{total_pro}g")

        if "food_knowledge" in context and context["food_knowledge"]:
            lines.append("\n相关食物营养知识（每100g）：")
            for f in context["food_knowledge"]:
                n = f["nutrition_per_100g"]
                lines.append(
                    f"  {f['name']}（{f['category']}）："
                    f"热量{n.get('calorie', '未知')}kcal，蛋白{n.get('protein', '未知')}g，"
                    f"脂肪{n.get('fat', '未知')}g，碳水{n.get('carb', '未知')}g"
                )

        if "weight" in context and context["weight"]:
            w = context["weight"]
            lines.append(
                f"\n体重趋势：当前{w['current']}kg，"
                f"{'上升' if w['change'] > 0 else '下降'}{abs(w['change'])}kg"
                f"（近30天，{w['records_count']}条记录）"
            )

        if "recipe" in context and context["recipe"]:
            lines.append("\n菜谱知识库检索（来源：HowToCook 开源菜谱库）：")
            for r in context["recipe"]:
                lines.append(f"[{r['citation']}] {r['title']} / {r['section']}")
                lines.append(r['content'])
                if r.get('distance') is not None:
                    score_text = f"余弦距离：{r['distance']:.4f}"
                else:
                    score_text = f"{r.get('retrieval_mode', 'retrieval')} 分数：{r.get('retrieval_score', 0):.4f}"
                lines.append(f"来源：{r['source']}；{score_text}")

        return "\n".join(lines) if lines else "（暂无用户数据）"
