#include "ProfileService.h"

#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QtGlobal>

#include "../config.h"
#include "ApiClient.h"

ProfileService &ProfileService::instance()
{
    static ProfileService s;
    return s;
}

ProfileService::ProfileService() = default;

void ProfileService::loadFromBackend(std::function<void(bool)> done)
{
    ApiClient &api = ApiClient::instance();
    // 1) 档案
    api.get(
        QStringLiteral("/api/profile?user_id=%1").arg(g_currentUserId),
        [this, done](const QJsonDocument &doc) {
            applyProfileFromJson(doc.object());
            if (done) done(true);
        },
        [this, done](const QString &err) {
            Q_UNUSED(err);
            if (done) done(false);
        });
    // 2) 体重记录
    api.get(
        QStringLiteral("/api/weight?user_id=%1").arg(g_currentUserId),
        [this](const QJsonDocument &doc) {
            applyWeightFromJson(doc.array());
        },
        nullptr);
}

void ProfileService::applyProfileFromJson(const QJsonObject &obj)
{
    const QStringList keys = obj.keys();
    if (!keys.isEmpty() && !obj.contains("nickname") && !obj.contains("gender"))
        return; // 不是有效的档案对象

    if (obj.contains("nickname"))        m_nickname = obj.value("nickname").toString();
    if (obj.contains("gender"))          m_gender = obj.value("gender").toString();
    if (obj.contains("age"))             m_age = obj.value("age").toInt();
    if (obj.contains("height_cm"))       m_heightCm = obj.value("height_cm").toDouble();
    if (obj.contains("weight_kg"))       m_weightKg = obj.value("weight_kg").toDouble();
    if (obj.contains("activity_level"))  m_activityLevel = obj.value("activity_level").toString();
    if (obj.contains("target_calorie"))  m_targetCal = obj.value("target_calorie").toDouble();
    if (obj.contains("allergens"))       m_allergens = obj.value("allergens").toString();
}

void ProfileService::applyWeightFromJson(const QJsonArray &arr)
{
    m_weightRecords.clear();
    int id = 1;
    for (const QJsonValue &v : arr) {
        const QJsonObject o = v.toObject();
        WeightRecord rec;
        rec.id = id++;
        rec.weightKg = o.value("weight_kg").toDouble();
        rec.date = QDate::fromString(o.value("record_date").toString(),
                                     QStringLiteral("yyyy-MM-dd"));
        if (!rec.date.isValid())
            rec.date = QDate::currentDate();
        m_weightRecords.append(rec);
    }
    std::sort(m_weightRecords.begin(), m_weightRecords.end(),
              [](const WeightRecord &a, const WeightRecord &b) { return a.date < b.date; });
    if (!m_weightRecords.isEmpty())
        m_weightKg = m_weightRecords.last().weightKg;
    m_nextWeightId = m_weightRecords.size() + 1;
}

void ProfileService::saveToBackend(std::function<void(bool, const QString &)> done)
{
    QJsonObject body;
    body["user_id"] = g_currentUserId;
    body["nickname"] = m_nickname;
    body["gender"] = m_gender;
    body["age"] = m_age;
    body["height_cm"] = m_heightCm;
    body["weight_kg"] = m_weightKg;
    body["activity_level"] = m_activityLevel;
    body["target_calorie"] = qRound(m_targetCal);
    body["allergens"] = m_allergens;

    ApiClient::instance().putJson(
        QStringLiteral("/api/profile"), body,
        [this, done](const QJsonDocument &) {
            // 档案保存成功后再提交今日体重记录
            submitTodayWeight(done);
        },
        [done](const QString &err) {
            if (done) done(false, QStringLiteral("档案保存失败: %1").arg(err));
        });
}

void ProfileService::submitTodayWeight(std::function<void(bool, const QString &)> done)
{
    // 查找今天的最新体重记录（有才提交）
    const QString today = QDate::currentDate().toString(QStringLiteral("yyyy-MM-dd"));
    double latestToday = 0.0;
    bool hasToday = false;
    for (auto it = m_weightRecords.crbegin(); it != m_weightRecords.crend(); ++it) {
        if (it->date.toString(QStringLiteral("yyyy-MM-dd")) == today) {
            latestToday = it->weightKg;
            hasToday = true;
            break;
        }
    }
    if (!hasToday) {
        if (done) done(true, QString());
        return;
    }

    QJsonObject body;
    body["user_id"] = g_currentUserId;
    body["weight_kg"] = latestToday;
    body["record_date"] = today;
    ApiClient::instance().postJson(
        QStringLiteral("/api/weight"), body,
        [done](const QJsonDocument &) {
            if (done) done(true, QString());
        },
        [done](const QString &err) {
            if (done) done(false, QStringLiteral("档案已保存，体重记录提交失败: %1").arg(err));
        });
}

void ProfileService::setWeightKg(double v, const QDate &date)
{
    m_weightKg = v;
    if (date.isValid())
        addWeightRecord(v, date);
}

double ProfileService::suggestTargetCalorie() const
{
    // Mifflin-St Jeor：BMR = 10*kg + 6.25*cm - 5*age + (男 +5 / 女 -161)
    double bmr = 10.0 * m_weightKg + 6.25 * m_heightCm - 5.0 * m_age;
    bmr += (m_gender == QStringLiteral("女")) ? -161.0 : 5.0;

    double factor = 1.375; // 默认轻度活动
    for (const auto &lv : AppConfig::kActivityLevels) {
        if (lv.name == m_activityLevel) {
            factor = lv.factor;
            break;
        }
    }
    return qRound(bmr * factor / 10.0) * 10.0; // 取整到 10
}

double ProfileService::bmi() const
{
    if (m_heightCm <= 0)
        return 0.0;
    const double m = m_heightCm / 100.0;
    return m_weightKg / (m * m);
}

QString ProfileService::bmiCategory() const
{
    const double b = bmi();
    if (b < 18.5)  return QStringLiteral("偏瘦");
    if (b < 24.0)  return QStringLiteral("正常");
    if (b < 28.0)  return QStringLiteral("超重");
    return QStringLiteral("肥胖");
}

QVector<WeightRecord> ProfileService::weightRecordsLast(int days) const
{
    const QDate since = QDate::currentDate().addDays(-days + 1);
    QVector<WeightRecord> result;
    for (const auto &r : m_weightRecords) {
        if (r.date >= since)
            result.append(r);
    }
    return result;
}

WeightRecord ProfileService::latestWeightRecord() const
{
    return m_weightRecords.isEmpty() ? WeightRecord{} : m_weightRecords.last();
}

int ProfileService::daysSinceLastWeight() const
{
    if (m_weightRecords.isEmpty())
        return -1;
    return m_weightRecords.last().date.daysTo(QDate::currentDate());
}

void ProfileService::addWeightRecord(double kg, const QDate &date)
{
    WeightRecord rec;
    rec.id = m_nextWeightId++;
    rec.weightKg = kg;
    rec.date = date.isValid() ? date : QDate::currentDate();
    // 按日期插入保持有序
    int insertPos = m_weightRecords.size();
    for (int i = 0; i < m_weightRecords.size(); ++i) {
        if (m_weightRecords.at(i).date > rec.date) {
            insertPos = i;
            break;
        }
    }
    m_weightRecords.insert(insertPos, rec);
    if (rec.date >= QDate::currentDate() || m_weightKg <= 0)
        m_weightKg = kg;
}

void ProfileService::removeWeightRecord(int id)
{
    for (int i = 0; i < m_weightRecords.size(); ++i) {
        if (m_weightRecords.at(i).id == id) {
            m_weightRecords.removeAt(i);
            break;
        }
    }
    if (!m_weightRecords.isEmpty())
        m_weightKg = m_weightRecords.last().weightKg;
}

double ProfileService::weightChangeDays(int days) const
{
    const auto recs = weightRecordsLast(days);
    if (recs.size() < 2)
        return 0.0;
    return recs.last().weightKg - recs.first().weightKg;
}
