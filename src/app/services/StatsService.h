#pragma once
// ============================================================
// 统计分析服务（接入后端 /api/stats/daily 和 /api/stats/weekly）
// 异步：从MySQL聚合统计，返回日/周报告
// ============================================================
#include <QDate>
#include <QMap>
#include <QObject>
#include <QString>
#include <QVector>

#include "../config.h"

struct DailySummary
{
    QDate date;
    double cal = 0.0, protein = 0.0, fat = 0.0, carb = 0.0;
    QMap<QString, double> mealCal;   // 餐次 -> 热量
};

struct WeeklySummary
{
    QStringList labels;           // 日期标签 M/d
    QVector<double> dailyCalories; // 每日热量
    double avgCal = 0, avgProtein = 0, avgFat = 0, avgCarb = 0;
    double targetCal = 2000;
    int daysWithData = 0;
};

// 运动统计（来自 /api/stats/exercise）
struct SportStat
{
    QString sport;
    double durationMin = 0.0, calories = 0.0, distanceKm = 0.0;
};

struct ExerciseDayStat
{
    bool hasPlan = false;
    QString planStatus;
    int taskTotal = 0, completedCount = 0;
    double completionRate = 0.0;
    double totalDurationMin = 0.0, totalCalories = 0.0, totalDistanceKm = 0.0;
    QVector<SportStat> bySport;
};

struct ExerciseWeekStat
{
    QStringList labels;
    QVector<double> dailyCalories, dailyDuration;
    int taskTotal = 0, completedCount = 0, activeDays = 0;
    double totalDurationMin = 0.0, totalCalories = 0.0;
    QVector<SportStat> bySport;
};

class StatsService : public QObject
{
    Q_OBJECT
public:
    static StatsService &instance();

    // 加载日统计（异步）
    void loadDaily(const QDate &date, int userId = g_currentUserId);
    // 加载周统计（异步）
    void loadWeekly(const QDate &endDate, int userId = g_currentUserId);
    // 运动统计
    void loadExerciseDay(const QDate &date, int userId = g_currentUserId);
    void loadExerciseWeek(const QDate &endDate, int userId = g_currentUserId);

    // 营养目标
    struct Targets { double cal, protein, fat, carb; };
    Targets targets() const;

signals:
    void dailyLoaded(const DailySummary &summary);
    void weeklyLoaded(const WeeklySummary &summary);
    void exerciseDayLoaded(const ExerciseDayStat &stat);
    void exerciseWeekLoaded(const ExerciseWeekStat &stat);
    void error(const QString &msg);

private:
    explicit StatsService(QObject *parent = nullptr);
    Q_DISABLE_COPY(StatsService)
    Targets m_targets{2000, 75, 67, 275};
};
