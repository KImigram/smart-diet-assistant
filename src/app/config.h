#pragma once
// ============================================================
// 全局配置：应用常量、餐次、活动水平、营养目标、AI/DB 占位说明
// ============================================================
#include <QString>
#include <QStringList>
#include <QVector>

namespace AppConfig {

inline const QString kAppName    = QStringLiteral("智能营养饮食助手");
inline const QString kVersion    = QStringLiteral("0.1.0");
inline const QString kOrgName    = QStringLiteral("HIT-WH-2304114");

// 餐次
inline const QStringList kMealTypes = {
    QStringLiteral("早餐"), QStringLiteral("午餐"),
    QStringLiteral("晚餐"), QStringLiteral("加餐")
};

// 活动水平（用于估算目标热量）
struct ActivityLevel { QString name; double factor; };
inline const QVector<ActivityLevel> kActivityLevels = {
    {QStringLiteral("久坐"), 1.2},
    {QStringLiteral("轻度活动"), 1.375},
    {QStringLiteral("中度活动"), 1.55},
    {QStringLiteral("高强度"), 1.725},
};

// 默认营养目标（热量取自健康档案，其余为默认值，可扩展）
inline const double kDefaultTargetCal     = 2000.0;
inline const double kDefaultTargetProtein = 60.0;
inline const double kDefaultTargetFat     = 65.0;
inline const double kDefaultTargetCarb    = 250.0;

// 营养素供能系数（kcal / g）
inline const double kKcalPerGramProtein = 4.0;
inline const double kKcalPerGramFat     = 9.0;
inline const double kKcalPerGramCarb    = 4.0;

// ------------------------------------------------------------
// AI 服务接入说明
// ------------------------------------------------------------
// 1) 菜品识别：MiniCPM-V 微调模型识别 + 基座模型二次校验
// 2) 对话生成：云端 OpenAI 兼容 API，结合营养知识 RAG 与用户数据
// 3) 数据存储：MySQL，参见 backend/database/schema.sql

} // namespace AppConfig

// 全局当前登录用户ID（登录后设置，所有 Service 默认使用）
inline int g_currentUserId = 1;
