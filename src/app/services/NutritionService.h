#pragma once
// ============================================================
// 营养计算引擎（食物营养成分库 + 按份量换算 + 关键词检索）
//
// 说明：当前食物库为内置演示数据（约 50 条）；
//       正式版由 MySQL 的 foods / food_categories / food_nutrition 表提供，
//       通过 DAO 替换本类的数据来源即可，接口保持不变。
// ============================================================
#include <QString>
#include <QStringList>
#include <QVector>

#include "../models/FoodItem.h"

class NutritionService
{
public:
    static NutritionService &instance();

    // 全部食物（演示库）
    const QVector<FoodItem> &allFoods() const { return m_foods; }

    // 按关键词模糊检索（名称/分类包含即命中；空关键词返回全部）
    QVector<FoodItem> searchFoods(const QString &keyword) const;

    // 按精确名称查找
    const FoodItem *findByName(const QString &name) const;

    // 按份量（克）换算实际摄入营养
    Nutrition calcAmount(const FoodItem &food, double portionG) const;

    // 格式化
    static QString formatKcal(double cal);       // "1234 kcal"
    static QString formatGram(double g);         // "45.2 g"

private:
    NutritionService();
    Q_DISABLE_COPY(NutritionService)

    QVector<FoodItem> m_foods;
};
