#include "StatsService.h"

#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>

#include "ApiClient.h"
#include "ProfileService.h"

StatsService &StatsService::instance()
{
    static StatsService s;
    return s;
}

StatsService::StatsService(QObject *parent)
    : QObject(parent)
{
}

StatsService::Targets StatsService::targets() const
{
    return m_targets;
}

void StatsService::loadDaily(const QDate &date, int userId)
{
    const QString dateStr = date.toString(QStringLiteral("yyyy-MM-dd"));
    ApiClient::instance().get(
        QStringLiteral("/api/stats/daily?date=%1&user_id=%2").arg(dateStr).arg(userId),
        [this, date](const QJsonDocument &doc) {
            QJsonObject o = doc.object();
            DailySummary s;
            s.date = date;
            QJsonObject total = o.value("total").toObject();
            s.cal = total.value("calorie").toDouble();
            s.protein = total.value("protein").toDouble();
            s.fat = total.value("fat").toDouble();
            s.carb = total.value("carb").toDouble();

            QJsonObject byMeal = o.value("by_meal").toObject();
            for (auto it = byMeal.begin(); it != byMeal.end(); ++it)
                s.mealCal[it.key()] = it.value().toDouble();

            // 更新目标
            QJsonObject tg = o.value("targets").toObject();
            m_targets.cal = tg.value("calorie").toDouble(2000);
            m_targets.protein = tg.value("protein").toDouble(75);
            m_targets.fat = tg.value("fat").toDouble(67);
            m_targets.carb = tg.value("carb").toDouble(275);

            emit dailyLoaded(s);
        },
        [this](const QString &err) {
            emit error(QStringLiteral("加载日统计失败: %1").arg(err));
        });
}

void StatsService::loadWeekly(const QDate &endDate, int userId)
{
    const QString dateStr = endDate.toString(QStringLiteral("yyyy-MM-dd"));
    ApiClient::instance().get(
        QStringLiteral("/api/stats/weekly?end_date=%1&user_id=%2").arg(dateStr).arg(userId),
        [this](const QJsonDocument &doc) {
            QJsonObject o = doc.object();
            WeeklySummary w;
            w.targetCal = o.value("target_calorie").toDouble(2000);
            w.daysWithData = o.value("days_with_data").toInt();

            QJsonArray labels = o.value("labels").toArray();
            for (const QJsonValue &v : labels)
                w.labels << v.toString();

            QJsonArray cals = o.value("daily_calories").toArray();
            for (const QJsonValue &v : cals)
                w.dailyCalories << v.toDouble();

            QJsonObject avg = o.value("average").toObject();
            w.avgCal = avg.value("calorie").toDouble();
            w.avgProtein = avg.value("protein").toDouble();
            w.avgFat = avg.value("fat").toDouble();
            w.avgCarb = avg.value("carb").toDouble();

            emit weeklyLoaded(w);
        },
        [this](const QString &err) {
            emit error(QStringLiteral("加载周统计失败: %1").arg(err));
        });
}

static void parseSportStats(const QJsonArray &arr, QVector<SportStat> &out)
{
    for (const QJsonValue &v : arr) {
        QJsonObject o = v.toObject();
        SportStat s;
        s.sport = o.value("sport").toString();
        s.durationMin = o.value("duration_min").toDouble();
        s.calories = o.value("calories").toDouble();
        s.distanceKm = o.value("distance_km").toDouble();
        out << s;
    }
}

void StatsService::loadExerciseDay(const QDate &date, int userId)
{
    const QString dateStr = date.toString(QStringLiteral("yyyy-MM-dd"));
    ApiClient::instance().get(
        QStringLiteral("/api/stats/exercise?mode=day&date=%1&user_id=%2")
            .arg(dateStr).arg(userId),
        [this](const QJsonDocument &doc) {
            QJsonObject o = doc.object();
            ExerciseDayStat s;
            s.hasPlan = o.value("has_plan").toBool();
            s.planStatus = o.value("plan_status").toString();
            s.taskTotal = o.value("task_total").toInt();
            s.completedCount = o.value("completed_count").toInt();
            s.completionRate = o.value("completion_rate").toDouble();
            s.totalDurationMin = o.value("total_duration_min").toDouble();
            s.totalCalories = o.value("total_calories").toDouble();
            s.totalDistanceKm = o.value("total_distance_km").toDouble();
            parseSportStats(o.value("by_sport").toArray(), s.bySport);
            emit exerciseDayLoaded(s);
        },
        [this](const QString &err) {
            emit error(QStringLiteral("加载运动日统计失败: %1").arg(err));
        });
}

void StatsService::loadExerciseWeek(const QDate &endDate, int userId)
{
    const QString dateStr = endDate.toString(QStringLiteral("yyyy-MM-dd"));
    ApiClient::instance().get(
        QStringLiteral("/api/stats/exercise?mode=week&date=%1&user_id=%2")
            .arg(dateStr).arg(userId),
        [this](const QJsonDocument &doc) {
            QJsonObject o = doc.object();
            ExerciseWeekStat s;
            s.taskTotal = o.value("task_total").toInt();
            s.completedCount = o.value("completed_count").toInt();
            s.activeDays = o.value("active_days").toInt();
            s.totalDurationMin = o.value("total_duration_min").toDouble();
            s.totalCalories = o.value("total_calories").toDouble();

            QJsonArray labels = o.value("labels").toArray();
            for (const QJsonValue &v : labels)
                s.labels << v.toString();
            QJsonArray cals = o.value("daily_calories").toArray();
            for (const QJsonValue &v : cals)
                s.dailyCalories << v.toDouble();
            QJsonArray mins = o.value("daily_duration").toArray();
            for (const QJsonValue &v : mins)
                s.dailyDuration << v.toDouble();
            parseSportStats(o.value("by_sport").toArray(), s.bySport);
            emit exerciseWeekLoaded(s);
        },
        [this](const QString &err) {
            emit error(QStringLiteral("加载运动周统计失败: %1").arg(err));
        });
}
