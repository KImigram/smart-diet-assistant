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
// AI 服务接入说明（尚未实现，占位）
// ------------------------------------------------------------
// 1) 菜品识别：百度智能云「菜品识别」接口（免费 500 次/天）
//    - 注册百度智能云账号，创建应用获取 API Key / Secret Key
//    - 通过 OAuth 获取 access_token，调用 dish 识别接口
//    - 返回菜名 + 置信度，由 RecognitionService 解析（见 services/RecognitionService.cpp 中 TODO）
// 2) 对话大模型：DeepSeek 开放平台
//    - 注册获取 API Key，调用 chat/completions 接口（流式）
//    - 结合结构化 RAG：先从 MySQL 检索健康档案/历史饮食记录/食物知识，拼接 prompt 后生成回答
// 3) 数据存储：MySQL 8.x，10 张表（见 sql/schema.sql），通过 DAO + 连接池访问

} // namespace AppConfig

// 全局当前登录用户ID（登录后设置，所有 Service 默认使用）
inline int g_currentUserId = 1;
