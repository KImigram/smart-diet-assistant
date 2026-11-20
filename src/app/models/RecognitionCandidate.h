#pragma once
// ============================================================
// 菜品识别候选实体（对应识别 API 返回结果）
// ============================================================
#include <QString>

struct RecognitionCandidate {
    QString  name;               // 识别出的菜品名
    double   confidence = 0.0;   // 置信度 0~1
    int      foodId = 0;         // 匹配到的本地食物ID（0=未匹配）
    QString  category;           // 食物分类
    QString  ingredients;        // 主要食材描述（基座模型补充，如"鸡肉, 米饭, 花生"）
    double   caloriePer100g = 0.0;  // 每100g热量
    double   proteinPer100g = 0.0;  // 每100g蛋白质
    bool     fromCorrection = false; // 是否来自纠错历史
};
