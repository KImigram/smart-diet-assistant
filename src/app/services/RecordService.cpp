#include "RecordService.h"

#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>

#include "ApiClient.h"
#include "NutritionService.h"

RecordService &RecordService::instance()
{
    static RecordService s;
    return s;
}

RecordService::RecordService(QObject *parent)
    : QObject(parent)
{
}

void RecordService::loadDate(const QDate &date, int userId)
{
    const QString dateStr = date.toString(QStringLiteral("yyyy-MM-dd"));
    ApiClient::instance().get(
        QStringLiteral("/api/meals?date=%1&user_id=%2").arg(dateStr).arg(userId),
        [this, date](const QJsonDocument &doc) {
            m_records.clear();
            const QJsonArray arr = doc.array();
            for (const QJsonValue &v : arr) {
                QJsonObject o = v.toObject();
                MealRecord r;
                r.id = o.value("id").toInt();
                r.foodName = o.value("food_name").toString();
                r.mealType = o.value("meal_type").toString();
                r.portionG = o.value("portion_g").toDouble();
                r.eatenAt = QDateTime::fromString(o.value("eaten_at").toString(),
                                                  QStringLiteral("yyyy-MM-dd HH:mm:ss"));
                // 营养数据
                QJsonObject n = o.value("nutrition").toObject();
                r.amount.cal = n.value("calorie").toDouble();
                r.amount.protein = n.value("protein").toDouble();
                r.amount.fat = n.value("fat").toDouble();
                r.amount.carb = n.value("carb").toDouble();
                r.amount.fiber = n.value("fiber").toDouble();
                r.amount.sodium = n.value("sodium").toDouble();
                m_records << r;
            }
            emit recordsLoaded(date, m_records);
        },
        [this](const QString &err) {
            emit error(QStringLiteral("加载记录失败: %1").arg(err));
        });
}

void RecordService::addRecord(int foodId, const QString &mealType,
                              double portionG, const QDateTime &eatenAt, int userId)
{
    QJsonObject body;
    body["user_id"] = userId;
    body["food_id"] = foodId;
    body["meal_type"] = mealType;
    body["portion_g"] = portionG;
    body["eaten_at"] = eatenAt.toString(QStringLiteral("yyyy-MM-dd HH:mm:ss"));

    ApiClient::instance().postJson(
        QStringLiteral("/api/meals"),
        body,
        [this](const QJsonDocument &doc) {
            QJsonObject o = doc.object();
            MealRecord r;
            r.id = o.value("id").toInt();
            r.foodName = o.value("food_name").toString();
            r.mealType = o.value("meal_type").toString();
            r.portionG = o.value("portion_g").toDouble();
            r.eatenAt = QDateTime::fromString(o.value("eaten_at").toString(),
                                              QStringLiteral("yyyy-MM-dd HH:mm:ss"));
            QJsonObject n = o.value("nutrition").toObject();
            r.amount.cal = n.value("calorie").toDouble();
            r.amount.protein = n.value("protein").toDouble();
            r.amount.fat = n.value("fat").toDouble();
            r.amount.carb = n.value("carb").toDouble();
            emit recordAdded(r);
        },
        [this](const QString &err) {
            emit error(QStringLiteral("添加记录失败: %1").arg(err));
        });
}

void RecordService::updateRecord(int id, double portionG)
{
    QJsonObject body;
    body["portion_g"] = portionG;

    // PATCH 请求
    ApiClient::instance().postJson(
        QStringLiteral("/api/meals/%1").arg(id),
        body,
        [this, id](const QJsonDocument &) {
            emit recordUpdated(id);
        },
        [this](const QString &err) {
            emit error(QStringLiteral("更新记录失败: %1").arg(err));
        });
}

void RecordService::deleteRecord(int id)
{
    // DELETE 请求 — 用 ApiClient 的 get 不行，需要扩展
    // 临时用 QNetworkAccessManager 直接发 DELETE
    auto *nam = new QNetworkAccessManager(this);
    QNetworkRequest req(QUrl(ApiClient::instance().baseUrl() +
                             QStringLiteral("/api/meals/%1").arg(id)));
    QNetworkReply *reply = nam->deleteResource(req);
    connect(reply, &QNetworkReply::finished, this, [this, id, reply, nam]() {
        reply->deleteLater();
        nam->deleteLater();
        emit recordDeleted(id);
    });
}
