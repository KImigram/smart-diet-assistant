#pragma once
// ============================================================
// 运动教练页面 v3
// 左侧：点击运动高亮 + 滑块调占比(10%步进,总和100%)
// 中间：今日计划（待确认/已确认）
// 右侧：打卡清单 + 达标状态卡（未达标灰度 / 已达标高光）
// ============================================================
#include <QDate>
#include <QVector>
#include <QWidget>

#include "../services/ExerciseService.h"

class QComboBox;
class QLabel;
class QFrame;
class QSlider;
class QPushButton;
class QScrollArea;
class QVBoxLayout;
class QHBoxLayout;
class QPropertyAnimation;

struct SportRow
{
    QString name;
    bool selected = false;
    int ratio = 0;          // 0-100
    QFrame *row = nullptr;
    QLabel *nameLabel = nullptr;
    QSlider *slider = nullptr;
    QLabel *pctLabel = nullptr;
};

class ExercisePage : public QWidget
{
    Q_OBJECT
public:
    explicit ExercisePage(QWidget *parent = nullptr);

    void refreshToday();

protected:
    bool eventFilter(QObject *obj, QEvent *ev) override;
    void showEvent(QShowEvent *ev) override;

private slots:
    void onGenerate();
    void onConfirm();
    void onCheckin(int taskIndex, bool completed);
    void onAnalyze();

private:
    void buildLeft(QHBoxLayout *root);
    void buildMiddle(QHBoxLayout *root);
    void buildRight(QHBoxLayout *root);

    void toggleSport(int index);
    void redistributeAfterToggle();
    void redistributeOnSlide(int changedIndex, int value);
    void updateSportRowsUI();
    void refreshRatioLabel();
    QString ratioText() const;
    void buildSportRows();
    static QString elide(const QString &s, int n);

    QFrame *makeEmptyState(const QString &emoji, const QString &title,
                           const QString &sub);
    void renderPlan(const ExercisePlan &plan);
    void renderCheckinList(const ExercisePlan &plan);
    QFrame *makeTaskRow(const ExerciseTask &task, bool editable);
    void renderDayResult(bool met, int done, int total,
                         const QStringList &reasons, const QString &advice,
                         double todayCal, double targetCal);
    void showToast(const QString &msg);
    void resizeEvent(QResizeEvent *ev) override;

    // 左
    QComboBox *m_goalCombo = nullptr;
    QVBoxLayout *m_sportRowsLay = nullptr;   // 运动行容器
    QLabel *m_ratioLabel = nullptr;
    QPushButton *m_btnGenerate = nullptr;
    QVector<SportRow> m_rows;

    // 中
    QLabel *m_planTitle = nullptr;
    QLabel *m_summary = nullptr;
    QScrollArea *m_cardsScroll = nullptr;   // 滑动切换容器（裁剪）
    QWidget *m_cardsHost = nullptr;         // 横向排布的卡片宿主
    QHBoxLayout *m_cardsLay = nullptr;
    QVector<QFrame *> m_taskCards;          // 与 m_plan.tasks 对齐
    int m_cardIndex = 0;
    QPushButton *m_btnPrev = nullptr;
    QPushButton *m_btnNext = nullptr;
    QLabel *m_pageLabel = nullptr;
    QPropertyAnimation *m_slideAnim = nullptr;
    QPushButton *m_btnConfirm = nullptr;
    QFrame *m_middleEmpty = nullptr;

    void renderTaskCards();                     // 重建任务卡（单卡展示）
    QFrame *makeTaskCard(const ExerciseTask &t, int idx);
    void showCard(int idx);                     // 带滑动动效切换
    void resizeCards();                         // 窗口变化时同步卡宽

    // 右
    QScrollArea *m_checkinScroll = nullptr;
    QWidget *m_checkinHost = nullptr;
    QVBoxLayout *m_checkinLay = nullptr;
    QVector<QFrame *> m_checkinRows;         // 打卡任务卡（铺满排列区）
    QLabel *m_checkinTitle = nullptr;
    QFrame *m_resultCard = nullptr;          // 达标状态卡（固定高度+内部滚动）
    QLabel *m_resultTitle = nullptr;
    QLabel *m_resultBody = nullptr;
    QScrollArea *m_resultScroll = nullptr;
    QPushButton *m_btnAnalyze = nullptr;
    QLabel *m_toast = nullptr;

    void layoutCheckins();                    // 任务卡均分铺满排列区

    ExercisePlan m_plan;
    QDate m_today;
    bool m_busy = false;
    static constexpr int kMaxSports = 3;      // 最多选择 3 项运动
    static constexpr int kTaskRowHeight = 88; // 打卡任务行固定高度（饱满）
};
