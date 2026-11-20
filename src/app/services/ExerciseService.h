#pragma once
// ============================================================
// 运动教练服务 v2
// 与当天饮食挂钩生成当日多任务计划 → 确认 → 简化打卡(完成/未完成) → 达标
// ============================================================
#include <QDate>
#include <QJsonObject>
#include <QObject>
#include <QString>
#include <QStringList>
#include <QVector>

#include "../config.h"

struct ExerciseTask
{
    QString sportType;
    QString title;
    QString content;
    int durationMin = 0;
    double distanceKm = 0.0;
    int calories = 0;
    int checkinId = 0;
    bool completed = false;
};

struct ExercisePlan
{
    int planId = 0;
    QString planDate;
    QString goal;
    QString status;      // pending / confirmed
    QString summary;
    QVector<ExerciseTask> tasks;
};

class ExerciseService : public QObject
{
    Q_OBJECT
public:
    static ExerciseService &instance();

    void loadTypes();
    // 生成：根据当天饮食 + 目标 + 偏好运动（多选，带占比，总和100%）
    void generatePlan(int userId, const QString &goal,
                      const QStringList &preferredSports,
                      const QJsonObject &preferredRatios);
    void loadToday(int userId, const QDate &date);
    void confirmPlan(int planId);
    void setCheckin(int checkinId, bool completed);
    void analyzeDay(int userId, int planId, const QDate &date);

signals:
    void typesLoaded(const QStringList &sportTypes, const QStringList &goals);
    void planLoaded(const ExercisePlan &plan);        // 今日计划（可能 status=pending）
    void planConfirmed(const ExercisePlan &plan);     // 确认后（含打卡清单）
    void checkinDone();
    void dayAnalyzed(bool met, int done, int total,
                     const QStringList &reasons, const QString &advice,
                     double todayCalorie, double targetCalorie);
    void error(const QString &msg);

private:
    explicit ExerciseService(QObject *parent = nullptr);
    Q_DISABLE_COPY(ExerciseService)

    ExercisePlan parsePlan(const QJsonObject &obj) const;
};
