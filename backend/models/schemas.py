"""Pydantic 请求/响应模型"""
from pydantic import BaseModel
from typing import Optional


class MealRecordCreate(BaseModel):
    user_id: int = 1
    food_id: int
    meal_type: str  # 早餐/午餐/晚餐/加餐
    portion_g: float
    eaten_at: Optional[str] = None


class MealRecordUpdate(BaseModel):
    portion_g: float


class WeightRecordCreate(BaseModel):
    user_id: int = 1
    weight_kg: float
    record_date: Optional[str] = None


class ProfileUpdate(BaseModel):
    user_id: int = 1
    nickname: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    target_calorie: Optional[int] = None
    activity_level: Optional[str] = None
    allergens: Optional[str] = None


class ChatRequest(BaseModel):
    user_id: int = 1
    session_id: Optional[int] = None
    message: str


class RecognitionRequest(BaseModel):
    user_id: int = 1
    image_base64: str


class CorrectionRequest(BaseModel):
    user_id: int = 1
    recognized_name: str
    correct_food_id: int


class AuthRequest(BaseModel):
    username: str
    password: str
    nickname: Optional[str] = None


class NutritionEstimateRequest(BaseModel):
    name: str          # 未收录的菜名
    user_id: int = 1   # 可选，用于自动写入纠错映射


class ExercisePlanRequest(BaseModel):
    user_id: int = 1
    goal: str = "综合提升"
    preferred_sports: list[str] = []   # 今天想做的运动（可多选）
    preferred_ratios: dict[str, int] = {}  # 运动占比 {运动: 百分比}，总和100
    plan_date: Optional[str] = None    # yyyy-MM-dd，默认今天


class ExerciseCheckin(BaseModel):
    checkin_id: int
    completed: bool


class ExerciseDayAnalyze(BaseModel):
    user_id: int = 1
    plan_id: int
    plan_date: Optional[str] = None
