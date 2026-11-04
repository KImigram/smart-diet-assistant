"""FastAPI 入口 — 智能营养饮食助手后端"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from config import APP_HOST, APP_PORT, DEFAULT_USER_ID
from models.schemas import (MealRecordCreate, MealRecordUpdate,
                            WeightRecordCreate, ProfileUpdate, ChatRequest,
                            RecognitionRequest, CorrectionRequest, AuthRequest,
                            NutritionEstimateRequest, ExercisePlanRequest,
                            ExerciseCheckin, ExerciseDayAnalyze)
from services.record_service import RecordService
from services.stats_service import StatsService
from services.nutrition_service import NutritionService
from services.chat_service import ChatService
from services.rag_service import RAGService
from services.recognition_service import RecognitionService
from services.exercise_service import ExerciseService, SPORT_TYPES, GOALS
from dao.food_dao import FoodDAO
from dao.user_dao import UserDAO
from dao.meal_dao import MealDAO
from dao.exercise_dao import ExerciseDAO

app = FastAPI(title="智能营养饮食助手 API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- 健康检查 ----------
@app.get("/api/health")
def health():
    return {"status": "ok", "service": "nutritious-diet-backend"}


# ---------- 用户认证 ----------
@app.post("/api/auth/register")
def register(data: AuthRequest):
    if len(data.username) < 2 or len(data.password) < 4:
        raise HTTPException(400, "用户名至少2位，密码至少4位")
    user_id = UserDAO.create_user(data.username, data.password, data.nickname)
    if user_id is None:
        raise HTTPException(409, "用户名已存在")
    return {"user_id": user_id, "username": data.username, "message": "注册成功"}


@app.post("/api/auth/login")
def login(data: AuthRequest):
    user_id = UserDAO.verify_user(data.username, data.password)
    if user_id is None:
        raise HTTPException(401, "用户名或密码错误")
    profile = UserDAO.get_profile(user_id)
    return {"user_id": user_id, "username": data.username,
            "nickname": profile.get("nickname", "") if profile else ""}


# ---------- 食物 ----------
@app.get("/api/foods/categories")
def list_categories():
    return FoodDAO.list_categories()


@app.get("/api/foods/search")
def search_food(q: str, limit: int = 20):
    return FoodDAO.search(q, limit)


@app.get("/api/foods/{food_id}")
def get_food(food_id: int):
    food = FoodDAO.get_by_id(food_id)
    if not food:
        raise HTTPException(404, "食物不存在")
    food["nutrition"] = FoodDAO.get_nutrition(food_id)
    return food


# ---------- 饮食记录 ----------
@app.post("/api/meals")
def add_meal(data: MealRecordCreate):
    return RecordService.add(data.user_id, data.food_id, data.meal_type,
                             data.portion_g, data.eaten_at)


@app.delete("/api/meals/{record_id}")
def delete_meal(record_id: int):
    MealDAO.delete(record_id)
    return {"ok": True}


@app.patch("/api/meals/{record_id}")
def update_meal(record_id: int, data: MealRecordUpdate):
    MealDAO.update_portion(record_id, data.portion_g)
    return {"ok": True}


@app.get("/api/meals")
def list_meals(date: str, user_id: int = DEFAULT_USER_ID):
    return RecordService.list_by_date(user_id, date)


@app.get("/api/meals/total")
def meal_total(date: str, user_id: int = DEFAULT_USER_ID):
    return RecordService.daily_total(user_id, date)


# ---------- 统计 ----------
@app.get("/api/stats/daily")
def stats_daily(date: str, user_id: int = DEFAULT_USER_ID):
    return StatsService.daily(user_id, date)


@app.get("/api/stats/weekly")
def stats_weekly(end_date: str = None, user_id: int = DEFAULT_USER_ID):
    return StatsService.weekly(user_id, end_date)


@app.get("/api/stats/exercise")
def stats_exercise(user_id: int = DEFAULT_USER_ID, mode: str = "day",
                   date: str = None):
    """运动统计：day=当天已完成打卡的运动汇总；week=最近7天运动趋势"""
    return ExerciseService.stats(user_id, mode, date)


# ---------- 用户/档案/体重 ----------
@app.get("/api/profile")
def get_profile(user_id: int = DEFAULT_USER_ID):
    profile = UserDAO.get_profile(user_id)
    if not profile:
        raise HTTPException(404, "用户不存在")
    return profile


@app.put("/api/profile")
def update_profile(data: ProfileUpdate):
    updates = {k: v for k, v in data.model_dump().items()
               if k != "user_id" and v is not None}
    if updates:
        UserDAO.update_profile(data.user_id, **updates)
    return {"ok": True}


@app.post("/api/weight")
def add_weight(data: WeightRecordCreate):
    from datetime import date
    record_date = data.record_date or date.today().strftime("%Y-%m-%d")
    UserDAO.add_weight(data.user_id, data.weight_kg, record_date)
    return {"ok": True}


@app.get("/api/weight")
def list_weight(days: int = 30, user_id: int = DEFAULT_USER_ID):
    return UserDAO.list_weight(user_id, days)


# ---------- 营养计算 ----------
@app.get("/api/nutrition/calc")
def calc_nutrition(food_id: int, portion_g: float):
    return NutritionService.calc(food_id, portion_g)


# ---------- AI 对话 ----------
@app.post("/api/chat/sessions")
def create_session(user_id: int = DEFAULT_USER_ID, title: str = "新对话"):
    session_id = ChatService.create_session(user_id, title)
    return {"session_id": session_id, "title": title}


@app.get("/api/chat/sessions")
def list_sessions(user_id: int = DEFAULT_USER_ID):
    return ChatService.list_sessions(user_id)


@app.get("/api/chat/sessions/{session_id}/messages")
def list_messages(session_id: int):
    return ChatService.list_messages(session_id)


@app.post("/api/chat")
def chat(data: ChatRequest):
    """发送消息，SSE 流式返回 AI 回复"""
    user_id = data.user_id
    session_id = data.session_id

    # 如果没有 session_id，自动创建一个
    if session_id is None:
        session_id = ChatService.create_session(user_id, "新对话")

    def generate():
        for chunk in ChatService.send_message(user_id, session_id, data.message):
            # SSE 格式：data: {json}\n\n
            import json
            yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/chat/sync")
def chat_sync(data: ChatRequest):
    """非流式对话（测试用），返回完整回复"""
    user_id = data.user_id
    session_id = data.session_id
    if session_id is None:
        session_id = ChatService.create_session(user_id, "新对话")
    reply = ChatService.send_message_sync(user_id, session_id, data.message)
    return {"session_id": session_id, "reply": reply}


@app.get("/api/rag/context")
def rag_context(question: str, user_id: int = DEFAULT_USER_ID):
    """调试用：查看 RAG 检索到的上下文"""
    context = RAGService.retrieve(user_id, question)
    return {"context": context, "formatted": RAGService._format_context(context)}


# ---------- 菜品识别（Tool Use） ----------
@app.post("/api/recognize")
def recognize_dish(data: RecognitionRequest):
    """
    菜品识别：接收base64图片，返回候选菜品列表。
    流程：百度API识别 → 匹配本地食物库 → 置信度判断 → 纠错优先
    """
    import base64, traceback
    try:
        image_bytes = base64.b64decode(data.image_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="图片base64解码失败")

    try:
        result = RecognitionService.recognize(image_bytes, data.user_id)
        return result
    except Exception as e:
        print(f"[RECOGNIZE ERROR] {type(e).__name__}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"识别服务异常: {type(e).__name__}: {e}")


@app.post("/api/recognize/correct")
def correct_recognition(data: CorrectionRequest):
    """记录用户纠错，后续识别优先匹配"""
    correction_id = RecognitionService.record_correction(
        data.user_id, data.recognized_name, data.correct_food_id
    )
    return {"correction_id": correction_id, "status": "ok"}


@app.post("/api/recognize/estimate")
def estimate_nutrition(data: NutritionEstimateRequest):
    """
    LLM 补全工具缺口：未收录菜名 → DeepSeek 估算营养 → 自动入库。
    后续识别同菜名直接命中本地库。
    """
    result = RecognitionService.estimate_and_add(data.name, data.user_id)
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "估算失败"))
    return result


# ---------- 运动教练 ----------
@app.get("/api/exercise/types")
def exercise_types():
    """支持的运动类型与目标（前端多选同源）"""
    return {"sport_types": SPORT_TYPES, "goals": GOALS}


@app.post("/api/exercise/plans/generate")
def generate_exercise_plan(data: ExercisePlanRequest):
    """根据【当天饮食摄入 + 目标 + 偏好运动及占比】由本地LLM生成当日多任务运动计划（待确认）"""
    return ExerciseService.generate_plan(
        data.user_id, data.goal, data.preferred_sports,
        data.preferred_ratios, data.plan_date)


@app.get("/api/exercise/plans/today")
def today_exercise_plan(user_id: int = DEFAULT_USER_ID,
                        plan_date: str | None = None):
    """查询当日计划（含任务与打卡状态）；无则返回 null"""
    return ExerciseService.today_plan(user_id, plan_date)


@app.get("/api/exercise/plans")
def list_exercise_plans(user_id: int = DEFAULT_USER_ID, days: int = 14):
    """历史计划列表"""
    return ExerciseService.list_plans_wrapper(user_id, days)


@app.get("/api/exercise/plans/{plan_id}")
def get_exercise_plan(plan_id: int):
    from dao.exercise_dao import ExerciseDAO
    plan = ExerciseDAO.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")
    return ExerciseService._plan_dict(plan, ExerciseDAO.list_checkins(plan_id))


@app.post("/api/exercise/plans/{plan_id}/confirm")
def confirm_exercise_plan(plan_id: int):
    """确认计划 → 生成当日打卡清单"""
    result = ExerciseService.confirm_plan(plan_id)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "确认失败"))
    return result


@app.post("/api/exercise/checkins")
def set_exercise_checkin(data: ExerciseCheckin):
    """打卡（简化）：仅确认任务完成/未完成"""
    ok = ExerciseService.set_checkin(data.checkin_id, data.completed)
    if not ok:
        raise HTTPException(status_code=404, detail="打卡项不存在")
    return {"ok": True}


@app.post("/api/exercise/analyze-day")
def analyze_exercise_day(data: ExerciseDayAnalyze):
    """当日计划完成情况 → 达标判定 + LLM建议（结合饮食）"""
    return ExerciseService.analyze_day(data.user_id, data.plan_id, data.plan_date)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)
