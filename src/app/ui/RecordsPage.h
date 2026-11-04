#pragma once
// ============================================================
// 界面 2 · 饮食记录页（接入后端API）
// 按日期查看/筛选/添加/编辑/删除饮食记录，顶部展示当日营养汇总
// ============================================================
#include <QDate>
#include <QVector>
#include <QWidget>

#include "../models/MealRecord.h"

class QComboBox;
class QDateEdit;
class QLabel;
class QPushButton;
class QTableWidget;
class MetricCard;

class RecordsPage : public QWidget
{
    Q_OBJECT
public:
    explicit RecordsPage(QWidget *parent = nullptr);

    void refresh();

private slots:
    void onPrevDay();
    void onNextDay();
    void onToday();
    void onAddRecord();
    void onEditRecord();
    void onDeleteRecord();
    void onRecordsLoaded(const QDate &date, const QVector<MealRecord> &records);
    void onRecordAdded(const MealRecord &record);
    void onRecordUpdated(int id);
    void onRecordDeleted(int id);
    void onError(const QString &msg);

private:
    QWidget *buildSummaryRow();
    void reloadTable();
    void updateSummary();
    QDate currentDate() const;

    QDateEdit       *m_dateEdit = nullptr;
    QComboBox       *m_mealFilter = nullptr;
    QTableWidget    *m_table = nullptr;
    QLabel          *m_toast = nullptr;

    MetricCard *m_cardCal = nullptr, *m_cardProtein = nullptr,
               *m_cardFat = nullptr, *m_cardCarb = nullptr;

    QVector<MealRecord> m_records;  // 当前日期的记录
};
