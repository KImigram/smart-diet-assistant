"""
菜品识别业务服务（Tool Use 调度层）
流程：图片 → 微调模型API识别菜名 → 匹配本地食物库 → 置信度判断 → 纠错回填

这是 Agent Tool Use 的典型实现：
1. 调用外部工具（本地微调识别服务：微调API识别菜名 + 基座模型裁决验证）获取原始结果
2. 用本地知识库（食物库）校验和丰富结果
3. 低置信度时触发用户确认/纠错
4. 纠错数据写库，识别结果优先展示、纠错结果作为第二候选追加（避免误伤真菜）
5. 未收录菜品 → 用大模型（DeepSeek/远程Ollama）估算营养并写入库（LLM 补全工具缺口）
"""
from ai.llm_client import get_llm
from ai.finetune_client import get_finetune_client
from dao.food_dao import FoodDAO
from dao.correction_dao import CorrectionDAO


class RecognitionService:
    """菜品识别调度服务"""

    # 置信度阈值：高于此值直接确认，低于则需要用户选择
    CONFIDENCE_THRESHOLD = 0.6

    @staticmethod
    def recognize(image_bytes: bytes, user_id: int = None) -> dict:
        """
        识别菜品图片，返回结构化结果。

        返回：
        {
            "candidates": [{"food_id", "name", "probability", "calorie_per_100g", "category", "ingredients"}],
            "need_confirm": bool,  # 低置信度时需要用户确认
            "top_match": {...} | None  # 高置信度时的最佳匹配
        }
        """
        # 1. 调用本地识别服务识别菜名（微调API识别 + 基座模型裁决验证）
        import requests
        try:
            client = get_finetune_client()
            raw_candidates = client.recognize_dish(image_bytes, top_num=5)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise RuntimeError("识别服务未启动，请先启动本地识别服务（127.0.0.1:8002）")

        # 2. 匹配本地食物库，丰富营养信息
        candidates = []
        for raw in raw_candidates:
            matched = RecognitionService._match_food(raw["name"])
            nut = (matched or {}).get("nutrition") or {}
            candidate = {
                "name": raw["name"],
                "probability": raw["probability"],
                "baidu_calorie": raw.get("calorie", ""),
                "ingredients": raw.get("ingredients", ""),
                "food_id": matched["id"] if matched else None,
                "category": matched.get("category", "未分类") if matched else "未分类",
                "calorie_per_100g": nut.get("calorie") if matched else None,
                "protein_per_100g": nut.get("protein") if matched else None,
                "fat_per_100g": nut.get("fat") if matched else None,
                "carb_per_100g": nut.get("carb") if matched else None,
                "fiber_per_100g": nut.get("fiber") if matched else None,
                "sodium_per_100g": nut.get("sodium") if matched else None,
            }
            candidates.append(candidate)

        # 3. 置信度判断
        top = candidates[0] if candidates else None
        need_confirm = (top is None or top["probability"] < RecognitionService.CONFIDENCE_THRESHOLD)

        # 4. 检查纠错历史：识别结果优先展示，纠错结果作为第二候选追加在下方
        if user_id and top:
            correction = CorrectionDAO.find_correction(top["name"])
            if correction:
                # 用户之前把这个识别结果纠正为别的菜
                corrected_food = FoodDAO.get_by_id(correction["corrected_food_id"])
                if corrected_food:
                    c_nut = corrected_food.get("nutrition") or {}
                    candidates.append({
                        "name": corrected_food["name"],
                        "probability": 0.99,  # 纠错结果标记为高置信
                        "baidu_calorie": "",
                        "ingredients": "",
                        "food_id": corrected_food["id"],
                        "category": corrected_food["category"],
                        "calorie_per_100g": c_nut.get("calorie"),
                        "protein_per_100g": c_nut.get("protein"),
                        "fat_per_100g": c_nut.get("fat"),
                        "carb_per_100g": c_nut.get("carb"),
                        "fiber_per_100g": c_nut.get("fiber"),
                        "sodium_per_100g": c_nut.get("sodium"),
                        "from_correction": True,
                    })
                    # 不改变 need_confirm：识别结果高置信时不强制确认，
                    # 纠错候选就在下方供用户选择，避免误伤真菜

        return {
            "candidates": candidates,
            "need_confirm": need_confirm,
            "top_match": candidates[0] if not need_confirm and candidates else None,
        }

    @staticmethod
    def _match_food(dish_name: str) -> dict | None:
        """
        将识别返回的菜名匹配到本地食物库。
        策略：精确匹配 → 包含匹配 → 返回None（未收录）
        """
        # 精确匹配
        food = FoodDAO.get_by_name(dish_name)
        if food:
            return food

        # 包含匹配（如"宫保鸡丁盖饭"匹配"宫保鸡丁"）
        all_foods = FoodDAO.search("", limit=200)
        for f in all_foods:
            if f["name"] in dish_name or dish_name in f["name"]:
                # search结果不含营养，用get_by_id补全
                return FoodDAO.get_by_id(f["id"])
        return None

    @staticmethod
    def record_correction(user_id: int, recognized_name: str,
                          correct_food_id: int) -> int:
        """
        记录用户纠错：识别结果是 recognized_name，用户选择了 correct_food_id。
        后续识别到相同菜名时优先推荐纠正后的结果。
        """
        return CorrectionDAO.add(user_id, recognized_name, correct_food_id)

    # ---- LLM 补全工具缺口：未收录菜品营养估算 + 自动入库 ----

    # 估算食物默认分类（未收录菜品入库时使用）
    ESTIMATED_CATEGORY = "家常菜"

    @staticmethod
    def estimate_and_add(dish_name: str, user_id: int = None) -> dict:
        """
        核心 Agent 兜底流程：
        1. 先查库：若已收录直接返回（避免重复估算）
        2. 调大模型估算每100g营养（LLM 补全工具缺口）
        3. 写入 foods + food_nutrition（自动入库）
        4. 返回估算结果，后续识别同菜名直接命中本地库

        返回：
        {
            "success": bool,
            "food_id": int | None,
            "name": str,
            "nutrition": {"calorie","protein","fat","carb","fiber","sodium"} | None,
            "source": "local" | "llm_estimated" | "failed",
            "error": str | None
        }
        """
        dish_name = (dish_name or "").strip()
        if not dish_name:
            return {"success": False, "error": "菜名为空"}

        # 1. 先查库，已收录直接返回
        existing = FoodDAO.get_by_name(dish_name)
        if existing:
            return {
                "success": True,
                "food_id": existing["id"],
                "name": dish_name,
                "nutrition": existing.get("nutrition") or {},
                "source": "local",
            }

        # 2. 调大模型估算
        llm = get_llm()
        if not llm.available:
            return {"success": False, "error": "未配置大模型 API Key，无法估算营养"}
        nutrition = llm.estimate_nutrition(dish_name)
        if not nutrition:
            return {"success": False, "error": "AI 营养估算失败，请稍后重试"}

        # 3. 确定分类并写入 foods
        category = FoodDAO.search("", limit=200)
        cat_id = None
        for f in category:
            if f["category"] == RecognitionService.ESTIMATED_CATEGORY:
                cat_id = f["category_id"]
                break
        if cat_id is None:
            cat_id = FoodDAO.add_category(RecognitionService.ESTIMATED_CATEGORY)

        food_id = FoodDAO.add_food(dish_name, cat_id, 150.0)
        if not food_id:
            return {"success": False, "error": "食物写入数据库失败"}

        # 4. 写入营养成分（每100g）
        for nutrient, value in nutrition.items():
            FoodDAO.set_nutrition(food_id, nutrient, value)

        # 5. 如果用户已登录，自动记录一条纠错映射（同菜名下次识别直接命中）
        if user_id:
            try:
                CorrectionDAO.add(user_id, dish_name, food_id)
            except Exception:
                pass

        return {
            "success": True,
            "food_id": food_id,
            "name": dish_name,
            "nutrition": nutrition,
            "source": "llm_estimated",
        }
