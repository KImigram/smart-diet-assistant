#include "StatsPage.h"

#include <QButtonGroup>
#include <QDate>
#include <QDateEdit>
#include <QDialog>
#include <QGridLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QPushButton>
#include <QScrollArea>
#include <QShowEvent>
#include <QVBoxLayout>

#include "../config.h"
#include "../services/ApiClient.h"
#include "../services/ProfileService.h"
#include "../services/StatsService.h"
#include "../widgets/BarChart.h"
#include "../widgets/DonutChart.h"
#include "../widgets/LineChart.h"
#include "../widgets/MetricCard.h"
#include "WeightRecordDialog.h"

#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>

namespace {
const QColor kGreen(0x2E, 0x9E, 0x6B), kBlue(0x3B, 0x82, 0xF6),
             kOrange(0xF5, 0xA6, 0x23), kPurple(0x8E, 0x6F, 0xD8),
             kRed(0xE5, 0x48, 0x4D);
}

StatsPage::StatsPage(QWidget *parent)
    : QWidget(parent)
{
    auto *root = new QVBoxLayout(this);
    root->setContentsMargins(0, 0, 0, 0);

    // 整页滚动：内容超高时滑动查看，不压缩原有卡片排版
    auto *scroll = new QScrollArea(this);
    scroll->setWidgetResizable(true);
    scroll->setFrameShape(QFrame::NoFrame);
    scroll->setStyleSheet(QStringLiteral(
        "QScrollArea{background:transparent;border:none;}"
        "QScrollArea > QWidget > QWidget{background:transparent;}"));
    auto *inner = new QWidget(scroll);
    auto *ilay = new QVBoxLayout(inner);
    ilay->setContentsMargins(24, 20, 24, 16);
    ilay->setSpacing(14);

    auto *header = new QHBoxLayout;
    auto *titleBox = new QVBoxLayout;
    auto *title = new QLabel(QStringLiteral("统计报告"), inner);
    title->setObjectName(QStringLiteral("PageTitle"));
    auto *subtitle = new QLabel(QStringLiteral("日/周营养与运动统计"), inner);
    subtitle->setObjectName(QStringLiteral("PageSubtitle"));
    titleBox->addWidget(title);
    titleBox->addWidget(subtitle);
    header->addLayout(titleBox);
    header->addStretch(1);

    m_btnDay = new QPushButton(QStringLiteral("日报告"), inner);
    m_btnDay->setObjectName(QStringLiteral("btnDay"));
    m_btnDay->setCheckable(true);
    m_btnDay->setChecked(true);
    m_btnWeek = new QPushButton(QStringLiteral("周报告"), inner);
    m_btnWeek->setObjectName(QStringLiteral("btnWeek"));
    m_btnWeek->setCheckable(true);
    auto *group = new QButtonGroup(this);
    group->setExclusive(true);
    group->addButton(m_btnDay);
    group->addButton(m_btnWeek);

    m_dateEdit = new QDateEdit(QDate::currentDate(), inner);
    m_dateEdit->setCalendarPopup(true);
    m_dateEdit->setDisplayFormat(QStringLiteral("yyyy-MM-dd"));
    m_dateEdit->setFixedWidth(130);

    header->addWidget(m_btnDay);
    header->addWidget(m_btnWeek);
    header->addSpacing(12);
    header->addWidget(m_dateEdit);
    ilay->addLayout(header);

    ilay->addWidget(buildChartsRow());
    ilay->addWidget(buildExerciseRow());
    ilay->addWidget(buildMetricsRow());
    ilay->addWidget(buildWeightCard());

    scroll->setWidget(inner);
    root->addWidget(scroll);

    connect(m_btnDay, &QPushButton::clicked, this, &StatsPage::onModeChanged);
    connect(m_btnWeek, &QPushButton::clicked, this, &StatsPage::onModeChanged);
    connect(m_dateEdit, &QDateEdit::dateChanged, this, [this]() { refresh(); });

    // 连接 StatsService 信号
    StatsService &ss = StatsService::instance();
    connect(&ss, &StatsService::dailyLoaded, this, &StatsPage::onDailyLoaded);
    connect(&ss, &StatsService::weeklyLoaded, this, &StatsPage::onWeeklyLoaded);
    connect(&ss, &StatsService::exerciseDayLoaded, this, &StatsPage::onExerciseDayLoaded);
    connect(&ss, &StatsService::exerciseWeekLoaded, this, &StatsPage::onExerciseWeekLoaded);
    connect(&ss, &StatsService::error, this, &StatsPage::onStatsError);

    refresh();
}

void StatsPage::showEvent(QShowEvent *ev)
{
    QWidget::showEvent(ev);
    // 每次进入统计报告页都重新拉取（打卡/饮食变化后保证数据最新）
    refresh();
}

QWidget *StatsPage::buildChartsRow()
{
    auto *row = new QWidget(this);
    auto *lay = new QHBoxLayout(row);
    lay->setContentsMargins(0, 0, 0, 0);
    lay->setSpacing(14);

    auto *barCard = new QFrame(row);
    barCard->setObjectName(QStringLiteral("Card"));
    auto *barLay = new QVBoxLayout(barCard);
    barLay->setContentsMargins(16, 12, 16, 12);
    m_barChart = new BarChart(barCard);
    barLay->addWidget(m_barChart);
    lay->addWidget(barCard, 3);

    auto *donutCard = new QFrame(row);
    donutCard->setObjectName(QStringLiteral("Card"));
    auto *donutLay = new QVBoxLayout(donutCard);
    donutLay->setContentsMargins(16, 12, 16, 12);
    m_donutChart = new DonutChart(donutCard);
    donutLay->addWidget(m_donutChart);
    lay->addWidget(donutCard, 2);

    return row;
}

QWidget *StatsPage::buildExerciseRow()
{
    auto *row = new QWidget(this);
    auto *lay = new QHBoxLayout(row);
    lay->setContentsMargins(0, 0, 0, 0);
    lay->setSpacing(14);

    auto *exCard = new QFrame(row);
    exCard->setObjectName(QStringLiteral("Card"));
    auto *exLay = new QVBoxLayout(exCard);
    exLay->setContentsMargins(16, 12, 16, 12);
    exLay->setSpacing(8);
    auto *exTitle = new QLabel(QStringLiteral("运动统计 · 已完成打卡"), exCard);
    exTitle->setObjectName(QStringLiteral("CardTitle"));
    m_exHint = new QLabel(QStringLiteral("打卡完成的运动才会计入统计"), exCard);
    m_exHint->setObjectName(QStringLiteral("HintText"));
    m_exHint->setWordWrap(true);
    m_exBarChart = new BarChart(exCard);
    m_exBarChart->setMinimumHeight(170);
    m_exDonutChart = new DonutChart(exCard);
    m_exDonutChart->setMinimumHeight(170);
    exLay->addWidget(exTitle);
    exLay->addWidget(m_exHint);
    exLay->addWidget(m_exBarChart, 1);
    exLay->addWidget(m_exDonutChart, 1);
    lay->addWidget(exCard, 1);
    return row;
}

QWidget *StatsPage::buildMetricsRow()
{
    auto *row = new QWidget(this);
    auto *lay = new QHBoxLayout(row);
    lay->setContentsMargins(0, 0, 0, 0);
    lay->setSpacing(12);

    m_mCal = new MetricCard(row);
    m_mProtein = new MetricCard(row);
    m_mFat = new MetricCard(row);
    m_mCarb = new MetricCard(row);
    lay->addWidget(m_mCal);
    lay->addWidget(m_mProtein);
    lay->addWidget(m_mFat);
    lay->addWidget(m_mCarb);
    return row;
}

QWidget *StatsPage::buildWeightCard()
{
    auto *card = new QFrame(this);
    card->setObjectName(QStringLiteral("Card"));
    auto *lay = new QVBoxLayout(card);
    lay->setContentsMargins(16, 12, 16, 12);
    lay->setSpacing(10);

    auto *titleRow = new QHBoxLayout;
    auto *wTitle = new QLabel(QStringLiteral("体重趋势"), card);
    wTitle->setObjectName(QStringLiteral("CardTitle"));
    m_btnAddWeight = new QPushButton(QStringLiteral("+ 记录体重"), card);
    m_btnAddWeight->setObjectName(QStringLiteral("GhostBtn"));
    m_btnAddWeight->setCursor(Qt::PointingHandCursor);
    m_btnAddWeight->setFixedHeight(30);
    titleRow->addWidget(wTitle);
    titleRow->addStretch(1);
    titleRow->addWidget(m_btnAddWeight);
    lay->addLayout(titleRow);

    m_weightInfo = new QLabel(card);
    m_weightInfo->setObjectName(QStringLiteral("HintText"));
    lay->addWidget(m_weightInfo);

    m_weightChart = new LineChart(card);
    m_weightChart->setUnit(QStringLiteral(" kg"));
    m_weightChart->setMinimumHeight(180);
    lay->addWidget(m_weightChart);

    connect(m_btnAddWeight, &QPushButton::clicked, this, &StatsPage::onAddWeight);
    return card;
}

void StatsPage::onAddWeight()
{
    WeightRecordDialog dlg(this);
    if (dlg.exec() == QDialog::Accepted) {
        const double newWeight = dlg.weightKg();
        const QDate newDate = dlg.date();
        // 写入后端
        QJsonObject body;
        body["user_id"] = g_currentUserId;
        body["weight_kg"] = newWeight;
        body["record_date"] = newDate.toString(QStringLiteral("yyyy-MM-dd"));
        ApiClient::instance().postJson(
            QStringLiteral("/api/weight"), body,
            [this, newWeight, newDate](const QJsonDocument &) {
                // 同步更新内存中的实时体重（档案/侧边栏/BMI/目标热量估算都会用到）
                ProfileService &pf = ProfileService::instance();
                pf.setWeightKg(newWeight, newDate);
                pf.notifyChanged();   // 通知侧边栏等界面刷新
                refreshWeight();      // 刷新统计页体重趋势
            },
            [](const QString &) {});
    }
}

void StatsPage::onModeChanged()
{
    m_weekMode = m_btnWeek->isChecked();
    m_dateEdit->setVisible(!m_weekMode);
    refresh();
}

void StatsPage::refresh()
{
    if (m_weekMode)
        refreshWeek();
    else
        refreshDay();
    refreshExercise();
    refreshWeight();
}

void StatsPage::refreshExercise()
{
    if (m_weekMode)
        StatsService::instance().loadExerciseWeek(m_dateEdit->date());
    else
        StatsService::instance().loadExerciseDay(m_dateEdit->date());
}

void StatsPage::refreshDay()
{
    StatsService::instance().loadDaily(m_dateEdit->date());
}

void StatsPage::refreshWeek()
{
    StatsService::instance().loadWeekly(m_dateEdit->date());
}

void StatsPage::onDailyLoaded(const DailySummary &ds)
{
    const StatsService::Targets tg = StatsService::instance().targets();

    m_barChart->setTitle(QStringLiteral("%1 · 各餐次热量")
                             .arg(ds.date.toString(QStringLiteral("M月d日"))));
    QStringList labels;
    QVector<double> values;
    for (const QString &meal : AppConfig::kMealTypes) {
        labels << meal;
        values << ds.mealCal.value(meal, 0.0);
    }
    m_barChart->setData(labels, values, -1.0, QStringLiteral("kcal"));

    const double pKcal = ds.protein * AppConfig::kKcalPerGramProtein;
    const double fKcal = ds.fat * AppConfig::kKcalPerGramFat;
    const double cKcal = ds.carb * AppConfig::kKcalPerGramCarb;
    m_donutChart->setTitle(QStringLiteral("三大营养素供能占比"));
    m_donutChart->setData(
        {QStringLiteral("蛋白质"), QStringLiteral("脂肪"), QStringLiteral("碳水")},
        {pKcal, fKcal, cKcal},
        {kGreen, kOrange, kPurple},
        QStringLiteral("摄入"), QStringLiteral("%1 kcal").arg(qRound(ds.cal)));

    m_mCal->setMetric(QStringLiteral("热量达标率"),
                      QStringLiteral("%1%").arg(tg.cal > 0 ? qRound(ds.cal / tg.cal * 100.0) : 0),
                      QStringLiteral("目标 %1 kcal").arg(qRound(tg.cal)),
                      tg.cal > 0 ? ds.cal / tg.cal : 0.0,
                      ds.cal > tg.cal ? kRed : kGreen);
    m_mProtein->setMetric(QStringLiteral("蛋白质达标率"),
                          QStringLiteral("%1%").arg(tg.protein > 0 ? qRound(ds.protein / tg.protein * 100.0) : 0),
                          QStringLiteral("目标 %1 g").arg(qRound(tg.protein)),
                          tg.protein > 0 ? ds.protein / tg.protein : 0.0, kBlue);
    m_mFat->setMetric(QStringLiteral("脂肪达标率"),
                      QStringLiteral("%1%").arg(tg.fat > 0 ? qRound(ds.fat / tg.fat * 100.0) : 0),
                      QStringLiteral("目标 %1 g").arg(qRound(tg.fat)),
                      tg.fat > 0 ? ds.fat / tg.fat : 0.0, kOrange);
    m_mCarb->setMetric(QStringLiteral("碳水达标率"),
                       QStringLiteral("%1%").arg(tg.carb > 0 ? qRound(ds.carb / tg.carb * 100.0) : 0),
                       QStringLiteral("目标 %1 g").arg(qRound(tg.carb)),
                       tg.carb > 0 ? ds.carb / tg.carb : 0.0, kPurple);
}

void StatsPage::onWeeklyLoaded(const WeeklySummary &w)
{
    m_barChart->setTitle(QStringLiteral("最近 7 天 · 每日热量（虚线为目标值）"));
    m_barChart->setData(w.labels, w.dailyCalories, w.targetCal, QStringLiteral("kcal"));

    const double pKcal = w.avgProtein * AppConfig::kKcalPerGramProtein;
    const double fKcal = w.avgFat * AppConfig::kKcalPerGramFat;
    const double cKcal = w.avgCarb * AppConfig::kKcalPerGramCarb;
    m_donutChart->setTitle(QStringLiteral("周平均营养素供能占比"));
    m_donutChart->setData(
        {QStringLiteral("蛋白质"), QStringLiteral("脂肪"), QStringLiteral("碳水")},
        {pKcal, fKcal, cKcal},
        {kGreen, kOrange, kPurple},
        QStringLiteral("日均"), QStringLiteral("%1 kcal").arg(qRound(w.avgCal)));

    m_mCal->setMetric(QStringLiteral("周均热量达标率"),
                      QStringLiteral("%1%").arg(w.targetCal > 0 ? qRound(w.avgCal / w.targetCal * 100.0) : 0),
                      QStringLiteral("目标 %1 kcal/天").arg(qRound(w.targetCal)),
                      w.targetCal > 0 ? w.avgCal / w.targetCal : 0.0,
                      w.avgCal > w.targetCal ? kRed : kGreen);
    m_mProtein->setMetric(QStringLiteral("周均蛋白质达标率"),
                          QStringLiteral("--"), QStringLiteral("g/天"), -1, kBlue);
    m_mFat->setMetric(QStringLiteral("周均脂肪达标率"),
                      QStringLiteral("--"), QStringLiteral("g/天"), -1, kOrange);
    m_mCarb->setMetric(QStringLiteral("周均碳水达标率"),
                       QStringLiteral("--"), QStringLiteral("g/天"), -1, kPurple);
}

void StatsPage::onStatsError(const QString &msg)
{
    Q_UNUSED(msg);
}

static QVector<QColor> sportColors(int n)
{
    static const QVector<QColor> kColors = {
        QColor(0x2E, 0x9E, 0x6B), QColor(0x3B, 0x82, 0xF6),
        QColor(0xF5, 0xA6, 0x23), QColor(0x8E, 0x6F, 0xD8),
        QColor(0xE5, 0x48, 0x4D), QColor(0x0E, 0xA5, 0xA4),
        QColor(0xD9, 0x77, 0x57), QColor(0x6B, 0x72, 0x80),
    };
    QVector<QColor> out;
    for (int i = 0; i < n; ++i)
        out << kColors.at(i % kColors.size());
    return out;
}

void StatsPage::onExerciseDayLoaded(const ExerciseDayStat &s)
{
    if (!s.hasPlan) {
        m_exBarChart->setTitle(QStringLiteral("今日无运动计划"));
        m_exBarChart->setData({}, {}, -1.0, QStringLiteral("kcal"));
        m_exDonutChart->setTitle(QStringLiteral("运动时长占比"));
        m_exDonutChart->setData({}, {}, {},
                                QStringLiteral("运动"), QStringLiteral("0 分钟"));
        m_exHint->setText(QStringLiteral(
            "今天还没有生成运动计划，去「运动教练」生成并打卡后，这里会展示运动消耗"));
        return;
    }

    // 柱状图：各运动类型消耗热量
    QStringList labels;
    QVector<double> values;
    for (const SportStat &sp : s.bySport) {
        labels << sp.sport;
        values << sp.calories;
    }
    m_exBarChart->setTitle(QStringLiteral("%1 · 各运动消耗")
                               .arg(m_dateEdit->date().toString(QStringLiteral("M月d日"))));
    m_exBarChart->setData(labels, values, -1.0, QStringLiteral("kcal"));

    // 环形图：运动时长占比
    QStringList dLabels;
    QVector<double> dValues;
    for (const SportStat &sp : s.bySport) {
        dLabels << sp.sport;
        dValues << sp.durationMin;
    }
    m_exDonutChart->setTitle(QStringLiteral("运动时长占比"));
    m_exDonutChart->setData(dLabels, dValues, sportColors(dLabels.size()),
                            QStringLiteral("运动"),
                            QStringLiteral("%1 分钟").arg(qRound(s.totalDurationMin)));

    QString status = s.planStatus == QLatin1String("confirmed")
                         ? QStringLiteral("计划已确认")
                         : QStringLiteral("计划待确认");
    m_exHint->setText(QStringLiteral(
        "%1 · 打卡 %2/%3 · 累计 %4 分钟 · %5 kcal · %6 km")
        .arg(status)
        .arg(s.completedCount).arg(s.taskTotal)
        .arg(qRound(s.totalDurationMin))
        .arg(qRound(s.totalCalories))
        .arg(QString::number(s.totalDistanceKm, 'f', 1)));
}

void StatsPage::onExerciseWeekLoaded(const ExerciseWeekStat &s)
{
    m_exBarChart->setTitle(QStringLiteral("最近 7 天 · 每日运动消耗"));
    m_exBarChart->setData(s.labels, s.dailyCalories, -1.0, QStringLiteral("kcal"));

    QStringList dLabels;
    QVector<double> dValues;
    for (const SportStat &sp : s.bySport) {
        dLabels << sp.sport;
        dValues << sp.durationMin;
    }
    m_exDonutChart->setTitle(QStringLiteral("7 天运动时长占比"));
    m_exDonutChart->setData(dLabels, dValues, sportColors(dLabels.size()),
                            QStringLiteral("运动"),
                            QStringLiteral("%1 分钟").arg(qRound(s.totalDurationMin)));

    m_exHint->setText(QStringLiteral(
        "7 天累计 %1 分钟 · %2 kcal · 打卡 %3/%4 · 活跃 %5 天")
        .arg(qRound(s.totalDurationMin))
        .arg(qRound(s.totalCalories))
        .arg(s.completedCount).arg(s.taskTotal)
        .arg(s.activeDays));
}

void StatsPage::refreshWeight()
{
    ApiClient::instance().get(
        QStringLiteral("/api/weight?days=30&user_id=%1").arg(g_currentUserId),
        [this](const QJsonDocument &doc) {
            m_weightRecords.clear();
            const QJsonArray arr = doc.array();
            for (const QJsonValue &v : arr) {
                QJsonObject o = v.toObject();
                WeightRecord r;
                r.id = o.value("id").toInt();
                r.weightKg = o.value("weight_kg").toDouble();
                r.date = QDate::fromString(o.value("record_date").toString(),
                                           QStringLiteral("yyyy-MM-dd"));
                m_weightRecords << r;
            }

            // 信息行
            ProfileService &pf = ProfileService::instance();
            const double bmi = pf.bmi();
            double current = pf.weightKg();
            double change = 0;
            if (m_weightRecords.size() >= 2) {
                current = m_weightRecords.last().weightKg;
                change = m_weightRecords.last().weightKg - m_weightRecords.first().weightKg;
            }

            QString changeStr;
            if (qAbs(change) < 0.05)
                changeStr = QStringLiteral("持平");
            else if (change < 0)
                changeStr = QStringLiteral("↓ %1 kg").arg(QString::number(-change, 'f', 1));
            else
                changeStr = QStringLiteral("↑ %1 kg").arg(QString::number(change, 'f', 1));

            m_weightInfo->setText(QStringLiteral(
                "当前 %1 kg · BMI %2（%3）· 近30天 %4")
                .arg(QString::number(current, 'f', 1))
                .arg(QString::number(bmi, 'f', 1))
                .arg(pf.bmiCategory())
                .arg(changeStr));

            // 折线图
            QStringList labels;
            QVector<double> values;
            for (const auto &r : m_weightRecords) {
                labels << r.date.toString(QStringLiteral("M/d"));
                values << r.weightKg;
            }
            m_weightChart->setData(labels, values, kGreen);
        },
        [](const QString &) {});
}
