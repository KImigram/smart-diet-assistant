#pragma once
// ============================================================
// 界面 3 · 统计报告页（接入后端API）
// 日/周维度：热量柱状图、三大营养素供能占比、达标率、体重趋势
// ============================================================
#include <QDate>
#include <QVector>
#include <QWidget>

#include "../models/WeightRecord.h"
#include "../services/StatsService.h"

class QDateEdit;
class QLabel;
class QPushButton;
class BarChart;
class DonutChart;
class LineChart;
class MetricCard;

class StatsPage : public QWidget
{
    Q_OBJECT
public:
    explicit StatsPage(QWidget *parent = nullptr);

    void refresh();

protected:
    void showEvent(QShowEvent *ev) override;

private slots:
    void onModeChanged();
    void onAddWeight();
    void onDailyLoaded(const DailySummary &summary);
    void onWeeklyLoaded(const WeeklySummary &summary);
    void onExerciseDayLoaded(const ExerciseDayStat &stat);
    void onExerciseWeekLoaded(const ExerciseWeekStat &stat);
    void onStatsError(const QString &msg);

private:
    void refreshDay();
    void refreshWeek();
    void refreshWeight();
    void refreshExercise();
    QWidget *buildChartsRow();
    QWidget *buildMetricsRow();
    QWidget *buildExerciseRow();
    QWidget *buildWeightCard();

    QPushButton *m_btnDay = nullptr;
    QPushButton *m_btnWeek = nullptr;
    QDateEdit   *m_dateEdit = nullptr;

    BarChart    *m_barChart = nullptr;
    DonutChart  *m_donutChart = nullptr;
    MetricCard  *m_mCal = nullptr, *m_mProtein = nullptr, *m_mFat = nullptr, *m_mCarb = nullptr;

    // 运动统计
    BarChart    *m_exBarChart = nullptr;
    DonutChart  *m_exDonutChart = nullptr;
    QLabel      *m_exHint = nullptr;

    // 体重趋势
    LineChart   *m_weightChart = nullptr;
    QLabel      *m_weightInfo = nullptr;
    QPushButton *m_btnAddWeight = nullptr;
    QVector<WeightRecord> m_weightRecords;

    bool m_weekMode = false;
};
