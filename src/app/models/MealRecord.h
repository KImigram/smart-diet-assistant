#pragma once
// ============================================================
// 饮食记录实体（对应数据库 meal_records 表）
// ============================================================
#include <QDateTime>
#include <QString>

#include "FoodItem.h"

struct MealRecord {
    int       id = 0;
    QString   foodName;    // 菜品名（冗余存储便于展示，正式版可只存 food_id）
    QString   category;    // 食物分类
    QString   mealType;    // 餐次：早餐/午餐/晚餐/加餐
    double    portionG = 0.0;   // 实际摄入份量（克）
    QDateTime eatenAt;         // 食用时间
    Nutrition amount;          // 按份量换算后的实际摄入量（快照）
};
