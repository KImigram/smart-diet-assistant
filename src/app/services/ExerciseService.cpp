#include "ExerciseService.h"

#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>

#include "ApiClient.h"

ExerciseService &ExerciseService::instance()
{
    static ExerciseService s;
    return s;
}

ExerciseService::ExerciseService(QObject *parent)
    : QObject(parent)
{
}

void ExerciseService::loadTypes()
{
    ApiClient::instance().get(
        QStringLiteral("/api/exercise/types"),
        [this](const QJsonDocument &doc) {
            const QJsonObject obj = doc.object();
            QStringList types, goals;
            const QJsonArray ta = obj.value("sport_types").toArray();
            for (const QJsonValue &v : ta) types << v.toString();
            const QJsonArray ga = obj.value("goals").toArray();
            for (const QJsonValue &v : ga) goals << v.toString();
            emit typesLoaded(types, goals);
        },
        [this](const QString &err) { emit error(QStringLiteral("加载运动类型失败: %1").arg(err)); });
}

void ExerciseService::generatePlan(int userId, const QString &goal,
                                   const QStringList &preferredSports,
                                   const QJsonObject &preferredRatios)
{
    QJsonArray sports;
    for (const QString &s : preferredSports) sports.append(s);
    QJsonObject body;
    body["user_id"] = userId;
    body["goal"] = goal;
    body["preferred_sports"] = sports;
    body["preferred_ratios"] = preferredRatios;
    ApiClient::instance().postJson(
        QStringLiteral("/api/exercise/plans/generate"), body,
        [this](const QJsonDocument &doc) {
            emit planLoaded(parsePlan(doc.object()));
        },
        [this](const QString &err) { emit error(QStringLiteral("生成计划失败: %1").arg(err)); });
}

void ExerciseService::loadToday(int userId, const QDate &date)
{
    ApiClient::instance().get(
        QStringLiteral("/api/exercise/plans/today?user_id=%1&plan_date=%2")
            .arg(userId).arg(date.toString(QStringLiteral("yyyy-MM-dd"))),
        [this](const QJsonDocument &doc) {
            if (doc.isNull() || doc.object().isEmpty())
                return;   // 今日无计划：前端显示空态
            emit planLoaded(parsePlan(doc.object()));
        },
        [this](const QString &err) { emit error(QStringLiteral("加载今日计划失败: %1").arg(err)); });
}

void ExerciseService::confirmPlan(int planId)
{
    ApiClient::instance().postJson(
        QStringLiteral("/api/exercise/plans/%1/confirm").arg(planId), QJsonObject(),
        [this](const QJsonDocument &doc) {
            const QJsonObject obj = doc.object();
            if (!obj.value("ok").toBool()) {
                emit error(obj.value("error").toString(QStringLiteral("确认失败")));
                return;
            }
            emit planConfirmed(parsePlan(obj.value("plan").toObject()));
        },
        [this](const QString &err) { emit error(QStringLiteral("确认计划失败: %1").arg(err)); });
}

void ExerciseService::setCheckin(int checkinId, bool completed)
{
    QJsonObject body;
    body["checkin_id"] = checkinId;
    body["completed"] = completed;
    ApiClient::instance().postJson(
        QStringLiteral("/api/exercise/checkins"), body,
        [this](const QJsonDocument &) { emit checkinDone(); },
        [this](const QString &err) { emit error(QStringLiteral("打卡失败: %1").arg(err)); });
}

void ExerciseService::analyzeDay(int userId, int planId, const QDate &date)
{
    QJsonObject body;
    body["user_id"] = userId;
    body["plan_id"] = planId;
    body["plan_date"] = date.toString(QStringLiteral("yyyy-MM-dd"));
    ApiClient::instance().postJson(
        QStringLiteral("/api/exercise/analyze-day"), body,
        [this](const QJsonDocument &doc) {
            const QJsonObject obj = doc.object();
            if (!obj.value("ok").toBool()) {
                emit error(obj.value("error").toString(QStringLiteral("达标分析失败")));
                return;
            }
            QStringList reasons;
            const QJsonArray ra = obj.value("reasons").toArray();
            for (const QJsonValue &v : ra) reasons << v.toString();
            emit dayAnalyzed(obj.value("met").toBool(),
                             obj.value("done").toInt(),
                             obj.value("total").toInt(),
                             reasons,
                             obj.value("advice").toString(QStringLiteral("")),
                             obj.value("today_calorie").toDouble(),
                             obj.value("target_calorie").toDouble());
        },
        [this](const QString &err) { emit error(QStringLiteral("达标分析失败: %1").arg(err)); });
}

ExercisePlan ExerciseService::parsePlan(const QJsonObject &obj) const
{
    ExercisePlan p;
    p.planId = obj.value("plan_id").toInt();
    p.planDate = obj.value("plan_date").toString();
    p.goal = obj.value("goal").toString();
    p.status = obj.value("status").toString(QStringLiteral("pending"));
    p.summary = obj.value("summary").toString(QStringLiteral(""));
    const QJsonArray arr = obj.value("tasks").toArray();
    for (const QJsonValue &v : arr) {
        const QJsonObject t = v.toObject();
        ExerciseTask e;
        e.sportType = t.value("sport_type").toString();
        e.title = t.value("title").toString();
        e.content = t.value("content").toString();
        e.durationMin = t.value("duration_min").toInt();
        e.distanceKm = t.value("distance_km").toDouble();
        e.calories = t.value("calories").toInt();
        e.checkinId = t.value("checkin_id").toInt();
        e.completed = t.value("completed").toBool();
        p.tasks.append(e);
    }
    return p;
}
