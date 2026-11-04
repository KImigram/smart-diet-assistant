#pragma once
// ============================================================
// 健康档案服务（对应数据库 users / health_profile / weight_records 表）
//
// 加载：GET /api/profile + /api/weight 从后端恢复
// 保存：PUT /api/profile 写档案；体重变化时 POST /api/weight
// ============================================================
#include <QDate>
#include <QString>
#include <QVector>
#include <functional>

#include "../models/WeightRecord.h"

class ProfileService
{
public:
    static ProfileService &instance();

    // ---- 基础信息 ----
    QString nickname() const { return m_nickname; }
    void setNickname(const QString &v) { m_nickname = v; }

    QString gender() const { return m_gender; }
    void setGender(const QString &v) { m_gender = v; }

    int age() const { return m_age; }
    void setAge(int v) { m_age = v; }

    double heightCm() const { return m_heightCm; }
    void setHeightCm(double v) { m_heightCm = v; }

    double weightKg() const { return m_weightKg; }
    // 设置当前体重；若 date 有效则同时追加一条体重记录
    void setWeightKg(double v, const QDate &date = QDate());

    QString activityLevel() const { return m_activityLevel; }
    void setActivityLevel(const QString &v) { m_activityLevel = v; }

    QString allergens() const { return m_allergens; }
    void setAllergens(const QString &v) { m_allergens = v; }

    // ---- 目标 ----
    double targetCalorie() const { return m_targetCal; }
    void setTargetCalorie(double v) { m_targetCal = v; }

    // 按 Mifflin-St Jeor 公式估算每日总消耗（TDEE）
    double suggestTargetCalorie() const;

    // ---- BMI ----
    double bmi() const;                       // 当前 BMI = kg / (m)^2
    QString bmiCategory() const;              // 偏瘦/正常/超重/肥胖

    // ---- 体重记录 ----
    const QVector<WeightRecord> &weightRecords() const { return m_weightRecords; }
    QVector<WeightRecord> weightRecordsLast(int days) const;  // 最近 N 天
    WeightRecord latestWeightRecord() const;                   // 最新一条
    int daysSinceLastWeight() const;                           // 距上次称重天数
    void addWeightRecord(double kg, const QDate &date = QDate::currentDate());
    void removeWeightRecord(int id);
    double weightChangeDays(int days) const;  // 最近 N 天体重变化（kg，负=减轻）

    // ---- 后端持久化 ----
    // 从后端加载档案+体重记录（启动/登录后调用），done(true) 表示成功
    void loadFromBackend(std::function<void(bool)> done = nullptr);
    // 将档案保存到后端；若今天有新体重记录则一并提交
    void saveToBackend(std::function<void(bool, const QString &)> done = nullptr);

    // ---- 全局变更通知 ----
    // 任何修改体重的入口（档案保存/新增体重记录）都应调用 notifyChanged()
    // 触发所有已注册界面（侧边栏/统计页等）刷新实时体重相关显示
    void setOnChanged(std::function<void()> cb) { m_onChanged = std::move(cb); }
    void notifyChanged() { if (m_onChanged) m_onChanged(); }

private:
    ProfileService();
    Q_DISABLE_COPY(ProfileService)

    void applyProfileFromJson(const QJsonObject &obj);
    void applyWeightFromJson(const QJsonArray &arr);
    void submitTodayWeight(std::function<void(bool, const QString &)> done);

    QString  m_nickname = QStringLiteral("用户");
    QString  m_gender   = QStringLiteral("男");
    int      m_age      = 22;
    double   m_heightCm = 175.0;
    double   m_weightKg = 65.0;
    QString  m_activityLevel = QStringLiteral("轻度活动");
    double   m_targetCal = 2000.0;
    QString  m_allergens;

    QVector<WeightRecord> m_weightRecords;
    int m_nextWeightId = 1;
    std::function<void()> m_onChanged;   // 体重/档案变更时的全局回调
};
