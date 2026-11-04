#pragma once
// ============================================================
// 饮食记录管理服务（接入后端 /api/meals）
// 异步：从MySQL加载记录，增删改通过API
// ============================================================
#include <QDate>
#include <QDateTime>
#include <QObject>
#include <QString>
#include <QVector>

#include "../config.h"
#include "../models/MealRecord.h"

class RecordService : public QObject
{
    Q_OBJECT
public:
    static RecordService &instance();

    // 加载某日记录（异步，完成后发出 recordsLoaded）
    void loadDate(const QDate &date, int userId = g_currentUserId);

    // 新增记录（异步，完成后发出 recordAdded）
    void addRecord(int foodId, const QString &mealType,
                   double portionG, const QDateTime &eatenAt, int userId = g_currentUserId);

    // 修改记录份量
    void updateRecord(int id, double portionG);

    // 删除记录
    void deleteRecord(int id);

    // 当前已加载的记录
    QVector<MealRecord> currentRecords() const { return m_records; }

signals:
    void recordsLoaded(const QDate &date, const QVector<MealRecord> &records);
    void recordAdded(const MealRecord &record);
    void recordUpdated(int id);
    void recordDeleted(int id);
    void error(const QString &msg);

private:
    explicit RecordService(QObject *parent = nullptr);
    Q_DISABLE_COPY(RecordService)
    QVector<MealRecord> m_records;
};
