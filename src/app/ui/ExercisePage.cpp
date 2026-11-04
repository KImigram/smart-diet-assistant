#include "ExercisePage.h"

#include <QComboBox>
#include <QEasingCurve>
#include <QEvent>
#include <QFrame>
#include <QHBoxLayout>
#include <QJsonObject>
#include <QLabel>
#include <QPropertyAnimation>
#include <QPushButton>
#include <QScrollArea>
#include <QShowEvent>
#include <QSlider>
#include <QVBoxLayout>

#include "../config.h"

ExercisePage::ExercisePage(QWidget *parent)
    : QWidget(parent)
    , m_today(QDate::currentDate())
{
    auto *root = new QVBoxLayout(this);
    root->setContentsMargins(24, 20, 24, 16);
    root->setSpacing(14);

    auto *title = new QLabel(QStringLiteral("运动教练"), this);
    title->setObjectName(QStringLiteral("PageTitle"));
    auto *subtitle = new QLabel(
        QStringLiteral("点击选择今天想做的运动，拖动滑块调整占比；AI 结合今日饮食生成计划，确认后打卡"), this);
    subtitle->setObjectName(QStringLiteral("PageSubtitle"));
    subtitle->setWordWrap(true);
    root->addWidget(title);
    root->addWidget(subtitle);

    auto *body = new QHBoxLayout;
    body->setSpacing(16);
    buildLeft(body);
    buildMiddle(body);
    buildRight(body);
    root->addLayout(body, 1);

    ExerciseService &es = ExerciseService::instance();
    connect(&es, &ExerciseService::typesLoaded, this, [this](const QStringList &types, const QStringList &goals) {
        for (const QString &t : types) {
            SportRow r;
            r.name = t;
            m_rows.append(r);
        }
        buildSportRows();
        m_goalCombo->clear();
        m_goalCombo->addItems(goals);
    });
    connect(&es, &ExerciseService::planLoaded, this, [this, &es](const ExercisePlan &p) {
        m_busy = false;
        m_btnGenerate->setEnabled(true);
        m_btnGenerate->setText(QStringLiteral("生成今日计划"));
        m_plan = p;
        renderPlan(p);
        if (p.status == QLatin1String("confirmed")) {
            renderCheckinList(p);
            es.analyzeDay(g_currentUserId, p.planId, m_today);
        }
    });
    connect(&es, &ExerciseService::planConfirmed, this, [this, &es](const ExercisePlan &p) {
        m_plan = p;
        renderPlan(p);
        renderCheckinList(p);
        showToast(QStringLiteral("✓ 计划已确认，打卡清单已生成"));
        es.analyzeDay(g_currentUserId, p.planId, m_today);
    });
    connect(&es, &ExerciseService::checkinDone, this, [this]() {
        ExerciseService::instance().loadToday(g_currentUserId, m_today);
    });
    connect(&es, &ExerciseService::dayAnalyzed, this,
            [this](bool met, int done, int total, const QStringList &reasons,
                   const QString &advice, double todayCal, double targetCal) {
                renderDayResult(met, done, total, reasons, advice, todayCal, targetCal);
            });
    connect(&es, &ExerciseService::error, this, [this](const QString &msg) {
        m_busy = false;
        m_btnGenerate->setEnabled(true);
        m_btnGenerate->setText(QStringLiteral("生成今日计划"));
        showToast(msg);
    });

    es.loadTypes();
    refreshToday();
}

void ExercisePage::refreshToday()
{
    ExerciseService::instance().loadToday(g_currentUserId, m_today);
}

void ExercisePage::showEvent(QShowEvent *ev)
{
    QWidget::showEvent(ev);
    // 每次进入页面都拉取当天计划：有则直接展示，无则待机
    m_today = QDate::currentDate();
    refreshToday();
}

bool ExercisePage::eventFilter(QObject *obj, QEvent *ev)
{
    if (ev->type() == QEvent::MouseButtonPress) {
        for (int i = 0; i < m_rows.size(); ++i) {
            if (m_rows[i].row == obj) {
                toggleSport(i);
                return true;
            }
        }
    }
    return QWidget::eventFilter(obj, ev);
}

// ---------------- 左侧：运动选择（点击高亮 + 滑块占比） ----------------
void ExercisePage::buildLeft(QHBoxLayout *root)
{
    auto *card = new QFrame(this);
    card->setObjectName(QStringLiteral("Card"));
    card->setFixedWidth(270);
    auto *lay = new QVBoxLayout(card);
    lay->setContentsMargins(16, 16, 16, 16);
    lay->setSpacing(10);

    auto *cardTitle = new QLabel(QStringLiteral("生成今日计划"), card);
    cardTitle->setObjectName(QStringLiteral("CardTitle"));

    auto *goalHint = new QLabel(QStringLiteral("我的目标"), card);
    goalHint->setObjectName(QStringLiteral("HintText"));
    m_goalCombo = new QComboBox(card);

    auto *sportHint = new QLabel(
        QStringLiteral("今天想做的运动（最多选 %1 项，点击选中，拖动滑块调占比）")
            .arg(kMaxSports),
        card);
    sportHint->setObjectName(QStringLiteral("HintText"));
    sportHint->setWordWrap(true);

    auto *scroll = new QScrollArea(card);
    scroll->setWidgetResizable(true);
    scroll->setFrameShape(QFrame::NoFrame);
    scroll->setStyleSheet(QStringLiteral("QScrollArea{background:transparent;border:none;}"));
    auto *host = new QWidget(scroll);
    m_sportRowsLay = new QVBoxLayout(host);
    m_sportRowsLay->setContentsMargins(0, 0, 0, 0);
    m_sportRowsLay->setSpacing(4);
    scroll->setWidget(host);

    m_ratioLabel = new QLabel(card);
    m_ratioLabel->setStyleSheet(QStringLiteral("color:#2E9E6B;font-size:12px;font-weight:600;"));

    m_btnGenerate = new QPushButton(QStringLiteral("生成今日计划"), card);
    m_btnGenerate->setObjectName(QStringLiteral("PrimaryBtn"));

    lay->addWidget(cardTitle);
    lay->addWidget(goalHint);
    lay->addWidget(m_goalCombo);
    lay->addWidget(sportHint);
    lay->addWidget(scroll, 1);
    lay->addWidget(m_ratioLabel);
    lay->addWidget(m_btnGenerate);

    connect(m_btnGenerate, &QPushButton::clicked, this, &ExercisePage::onGenerate);
    root->addWidget(card);
}

void ExercisePage::buildSportRows()
{
    while (m_sportRowsLay->count())
        delete m_sportRowsLay->takeAt(0)->widget();
    for (auto &r : m_rows) {
        r.row = new QFrame(this);
        r.row->setCursor(Qt::PointingHandCursor);
        r.row->installEventFilter(this);
        auto *lay = new QHBoxLayout(r.row);
        lay->setContentsMargins(10, 6, 10, 6);
        lay->setSpacing(6);

        r.nameLabel = new QLabel(r.name, r.row);
        r.nameLabel->setFixedWidth(52);
        r.nameLabel->setStyleSheet(QStringLiteral("border:none;font-size:13px;color:#5C6F82;"));

        r.slider = new QSlider(Qt::Horizontal, r.row);
        r.slider->setRange(0, 100);
        r.slider->setSingleStep(10);
        r.slider->setPageStep(10);
        r.slider->setFixedWidth(90);
        r.slider->setVisible(false);
        r.slider->setStyleSheet(QStringLiteral(
            "QSlider::groove:horizontal{height:4px;background:#E4E9EE;border-radius:2px;}"
            "QSlider::sub-page:horizontal{background:#2E9E6B;border-radius:2px;}"
            "QSlider::handle:horizontal{width:12px;height:12px;margin:-4px 0;background:white;"
            "border:2px solid #2E9E6B;border-radius:6px;}"));

        r.pctLabel = new QLabel(QStringLiteral("—"), r.row);
        r.pctLabel->setFixedWidth(34);
        r.pctLabel->setAlignment(Qt::AlignRight | Qt::AlignVCenter);
        r.pctLabel->setStyleSheet(QStringLiteral("border:none;font-size:12px;color:#2E9E6B;font-weight:600;"));

        lay->addWidget(r.nameLabel);
        lay->addWidget(r.slider);
        lay->addWidget(r.pctLabel);
        m_sportRowsLay->addWidget(r.row);

        const int idx = int(&r - m_rows.data());
        connect(r.slider, &QSlider::valueChanged, this, [this, idx](int v) {
            redistributeOnSlide(idx, v);
        });
    }
    m_sportRowsLay->addStretch(1);
    refreshRatioLabel();
}

void ExercisePage::toggleSport(int index)
{
    if (index < 0 || index >= m_rows.size()) return;
    if (!m_rows[index].selected) {
        int cnt = 0;
        for (const auto &r : m_rows)
            if (r.selected) ++cnt;
        if (cnt >= kMaxSports) {
            showToast(QStringLiteral("最多选择 %1 项运动（当前已选 %2 项）")
                          .arg(kMaxSports).arg(cnt));
            return;
        }
    }
    m_rows[index].selected = !m_rows[index].selected;
    const bool nowSel = m_rows[index].selected;
    redistributeAfterToggle();
    updateSportRowsUI();
    refreshRatioLabel();
    if (nowSel) {
        showToast(QStringLiteral("已选择「%1」，当前占比 %2%")
                      .arg(m_rows[index].name).arg(m_rows[index].ratio));
    } else {
        showToast(QStringLiteral("已取消「%1」").arg(m_rows[index].name));
    }
}

QString ExercisePage::elide(const QString &s, int n)
{
    return s.size() <= n ? s : s.left(n) + QStringLiteral("…");
}

void ExercisePage::redistributeAfterToggle()
{
    QVector<int> sel;
    for (int i = 0; i < m_rows.size(); ++i)
        if (m_rows[i].selected) sel << i;
    if (sel.isEmpty()) return;
    // 均分（10%步进，余数加给前几项）
    const int base = (100 / sel.size() / 10) * 10;
    for (int i : sel) m_rows[i].ratio = base;
    int remain = 100 - base * sel.size();
    for (int i : sel) {
        if (remain <= 0) break;
        m_rows[i].ratio += 10;
        remain -= 10;
    }
    // 同步滑块
    for (int i = 0; i < m_rows.size(); ++i)
        if (m_rows[i].slider) m_rows[i].slider->blockSignals(true);
    for (int i : sel) if (m_rows[i].slider) m_rows[i].slider->setValue(m_rows[i].ratio);
    for (int i = 0; i < m_rows.size(); ++i)
        if (m_rows[i].slider) m_rows[i].slider->blockSignals(false);
}

void ExercisePage::redistributeOnSlide(int changedIndex, int value)
{
    // 每 10% 自动吸附
    const int snapped = (value + 5) / 10 * 10;
    if (snapped != value) {
        m_rows[changedIndex].slider->blockSignals(true);
        m_rows[changedIndex].slider->setValue(snapped);
        m_rows[changedIndex].slider->blockSignals(false);
        value = snapped;
    }
    m_rows[changedIndex].ratio = value;
    QVector<int> others;
    int otherTotal = 0;
    for (int i = 0; i < m_rows.size(); ++i) {
        if (i != changedIndex && m_rows[i].selected) {
            others << i;
            otherTotal += m_rows[i].ratio;
        }
    }
    if (!others.isEmpty() && otherTotal > 0) {
        const int remain = 100 - value;
        const double scale = double(remain) / otherTotal;
        for (int j : others) {
            int nv = int(m_rows[j].ratio * scale / 10.0 + 0.5) * 10;
            m_rows[j].ratio = qBound(0, nv, 100);
        }
        // 尾差校正：确保总和=100
        int sum = value;
        for (int j : others) sum += m_rows[j].ratio;
        int delta = 100 - sum;
        if (delta != 0 && !others.isEmpty())
            m_rows[others[0]].ratio = qBound(0, m_rows[others[0]].ratio + delta, 100);
    }
    for (int i = 0; i < m_rows.size(); ++i) {
        if (m_rows[i].slider) m_rows[i].slider->blockSignals(true);
        if (m_rows[i].selected && i != changedIndex)
            m_rows[i].slider->setValue(m_rows[i].ratio);
        if (m_rows[i].slider) m_rows[i].slider->blockSignals(false);
    }
    updateSportRowsUI();
    refreshRatioLabel();
    showToast(QStringLiteral("占比：%1").arg(ratioText()));
}

void ExercisePage::updateSportRowsUI()
{
    for (auto &r : m_rows) {
        const bool sel = r.selected;
        r.row->setStyleSheet(sel
            ? QStringLiteral("QFrame{background:#EAF6F0;border:1px solid #2E9E6B;border-radius:8px;}")
            : QStringLiteral("QFrame{background:#FFFFFF;border:1px solid #E4E9EE;border-radius:8px;}"));
        r.nameLabel->setStyleSheet(sel
            ? QStringLiteral("border:none;font-size:13px;color:#1F7A52;font-weight:600;")
            : QStringLiteral("border:none;font-size:13px;color:#5C6F82;"));
        r.slider->setVisible(sel);
        r.pctLabel->setText(sel ? QStringLiteral("%1%").arg(r.ratio) : QStringLiteral("—"));
    }
}

// 实时占比文本（toast 用）
QString ExercisePage::ratioText() const
{
    QStringList parts;
    for (const auto &r : m_rows)
        if (r.selected)
            parts << QStringLiteral("%1 %2%").arg(r.name).arg(r.ratio);
    return parts.isEmpty() ? QStringLiteral("未选择运动")
                           : parts.join(QStringLiteral(" · "));
}

void ExercisePage::refreshRatioLabel()
{
    int sum = 0, cnt = 0;
    for (const auto &r : m_rows) {
        if (r.selected) { sum += r.ratio; ++cnt; }
    }
    m_ratioLabel->setText(cnt > 0
        ? QStringLiteral("已分配 %1% · %2 项运动（共 100%）").arg(sum).arg(cnt)
        : QStringLiteral("尚未选择运动（共 100%）"));
    m_ratioLabel->setStyleSheet(sum == 100 && cnt > 0
        ? QStringLiteral("color:#2E9E6B;font-size:12px;font-weight:600;")
        : QStringLiteral("color:#C2410C;font-size:12px;font-weight:600;"));
}

// ---------------- 中间：今日计划 ----------------
void ExercisePage::buildMiddle(QHBoxLayout *root)
{
    auto *card = new QFrame(this);
    card->setObjectName(QStringLiteral("Card"));
    auto *lay = new QVBoxLayout(card);
    lay->setContentsMargins(16, 16, 16, 16);
    lay->setSpacing(10);

    auto *cardTitle = new QLabel(QStringLiteral("今日运动计划"), card);
    cardTitle->setObjectName(QStringLiteral("CardTitle"));
    m_planTitle = new QLabel(QStringLiteral("今日运动计划"), card);
    m_planTitle->setObjectName(QStringLiteral("CardTitle"));
    m_planTitle->setStyleSheet(QStringLiteral("font-size:13px;color:#22303F;font-weight:500;"));

    m_summary = new QLabel(card);
    m_summary->setWordWrap(true);
    m_summary->setFixedHeight(74);
    m_summary->setAlignment(Qt::AlignTop | Qt::AlignLeft);
    m_summary->setStyleSheet(QStringLiteral("background:#FFFFFF;border-radius:12px;padding:10px;"
                                            "color:#33424F;font-size:13px;border:1px solid #E4E9EE;"));
    m_summary->setVisible(false);

    m_middleEmpty = makeEmptyState(
        QStringLiteral("🏃"),
        QStringLiteral("还没有今日计划"),
        QStringLiteral("左侧点击选择想做的运动，拖动滑块调好占比，再点「生成今日计划」"));

    // 滑动切换容器：单卡展示，多卡滑动切换，点击卡片展开详情
    m_cardsScroll = new QScrollArea(card);
    m_cardsScroll->setWidgetResizable(false);
    m_cardsScroll->setFrameShape(QFrame::NoFrame);
    m_cardsScroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
    m_cardsScroll->setVerticalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
    m_cardsScroll->setStyleSheet(QStringLiteral(
        "QScrollArea{background:#FFFFFF;border:1px solid #E4E9EE;border-radius:12px;}"));
    m_cardsHost = new QWidget(m_cardsScroll);
    m_cardsHost->setStyleSheet(QStringLiteral("background:transparent;"));
    m_cardsLay = new QHBoxLayout(m_cardsHost);
    m_cardsLay->setContentsMargins(0, 0, 0, 0);
    m_cardsLay->setSpacing(0);
    m_cardsScroll->setWidget(m_cardsHost);
    m_cardsScroll->setVisible(false);

    // 导航：← 1/3 →（用常见箭头字符，避免 ◀▶ 渲染空白）
    auto *nav = new QHBoxLayout;
    nav->setSpacing(8);
    m_btnPrev = new QPushButton(QStringLiteral("←"), card);
    m_btnPrev->setObjectName(QStringLiteral("GhostBtn"));
    m_btnPrev->setFixedSize(30, 26);
    m_btnPrev->setCursor(Qt::PointingHandCursor);
    m_btnPrev->setToolTip(QStringLiteral("上一项"));
    m_pageLabel = new QLabel(QStringLiteral("1/1"), card);
    m_pageLabel->setAlignment(Qt::AlignCenter);
    m_pageLabel->setStyleSheet(QStringLiteral("color:#5C6F82;font-size:12px;font-weight:600;"));
    m_pageLabel->setMinimumWidth(40);
    m_btnNext = new QPushButton(QStringLiteral("→"), card);
    m_btnNext->setObjectName(QStringLiteral("GhostBtn"));
    m_btnNext->setFixedSize(30, 26);
    m_btnNext->setCursor(Qt::PointingHandCursor);
    m_btnNext->setToolTip(QStringLiteral("下一项"));
    nav->addStretch(1);
    nav->addWidget(m_btnPrev);
    nav->addWidget(m_pageLabel);
    nav->addWidget(m_btnNext);
    nav->addStretch(1);

    m_btnConfirm = new QPushButton(QStringLiteral("确认计划，生成打卡清单"), card);
    m_btnConfirm->setObjectName(QStringLiteral("PrimaryBtn"));
    m_btnConfirm->setVisible(false);

    lay->addWidget(cardTitle);
    lay->addWidget(m_planTitle);
    lay->addWidget(m_summary);
    lay->addWidget(m_middleEmpty);
    lay->addWidget(m_cardsScroll, 1);
    lay->addLayout(nav);
    lay->addWidget(m_btnConfirm);

    connect(m_btnConfirm, &QPushButton::clicked, this, &ExercisePage::onConfirm);
    connect(m_btnPrev, &QPushButton::clicked, this, [this]() {
        if (m_taskCards.size() > 1) showCard((m_cardIndex - 1 + m_taskCards.size())
                                             % m_taskCards.size());
    });
    connect(m_btnNext, &QPushButton::clicked, this, [this]() {
        if (m_taskCards.size() > 1) showCard((m_cardIndex + 1) % m_taskCards.size());
    });
    root->addWidget(card, 2);
}

// ---------------- 右侧：打卡清单 + 达标状态卡 ----------------
void ExercisePage::buildRight(QHBoxLayout *root)
{
    auto *card = new QFrame(this);
    card->setObjectName(QStringLiteral("Card"));
    card->setFixedWidth(400);
    // 显式强制白底，与主题同色
    card->setStyleSheet(QStringLiteral(
        "QFrame#Card{background:#FFFFFF;border:1px solid #E4E9EE;border-radius:12px;}"));
    auto *lay = new QVBoxLayout(card);
    lay->setContentsMargins(16, 16, 16, 16);
    lay->setSpacing(10);

    m_checkinTitle = new QLabel(QStringLiteral("今日打卡清单"), card);
    m_checkinTitle->setObjectName(QStringLiteral("CardTitle"));

    // 打卡排列区：白底（不加深），卡片纵向均分铺满
    auto *scroll = new QScrollArea(card);
    m_checkinScroll = scroll;
    scroll->setWidgetResizable(true);
    scroll->setFrameShape(QFrame::NoFrame);
    scroll->setStyleSheet(QStringLiteral(
        "QScrollArea{background:#FFFFFF;border:1px solid #E4E9EE;border-radius:12px;}"));
    auto *checkinHost = new QWidget(scroll);
    m_checkinHost = checkinHost;
    checkinHost->setStyleSheet(QStringLiteral("background:#FFFFFF;"));
    m_checkinLay = new QVBoxLayout(checkinHost);
    m_checkinLay->setContentsMargins(10, 10, 10, 10);
    m_checkinLay->setSpacing(8);
    scroll->setWidget(checkinHost);

    m_resultCard = new QFrame(card);
    m_resultCard->setFixedHeight(170);
    m_resultCard->setStyleSheet(QStringLiteral("QFrame{background:#FFFFFF;border-radius:12px;"
                                               "border:1px solid #E4E9EE;}"));
    auto *rLay = new QVBoxLayout(m_resultCard);
    rLay->setContentsMargins(14, 10, 14, 10);
    rLay->setSpacing(6);
    m_resultTitle = new QLabel(m_resultCard);
    m_resultTitle->setStyleSheet(QStringLiteral("border:none;font-size:15px;font-weight:700;color:#8A99A9;"));
    // 教练评语：固定高度 + 内部滚动，不随字数改变卡片大小
    m_resultScroll = new QScrollArea(m_resultCard);
    m_resultScroll->setWidgetResizable(true);
    m_resultScroll->setFrameShape(QFrame::NoFrame);
    m_resultScroll->setStyleSheet(QStringLiteral("QScrollArea{background:transparent;border:none;}"));
    auto *rBodyHost = new QWidget(m_resultScroll);
    auto *rBodyLay = new QVBoxLayout(rBodyHost);
    rBodyLay->setContentsMargins(0, 0, 0, 0);
    rBodyLay->addStretch(1);
    m_resultBody = new QLabel(rBodyHost);
    m_resultBody->setWordWrap(true);
    m_resultBody->setAlignment(Qt::AlignTop | Qt::AlignLeft);
    m_resultBody->setStyleSheet(QStringLiteral("border:none;font-size:12px;color:#8A99A9;"));
    rBodyLay->insertWidget(0, m_resultBody);
    m_resultScroll->setWidget(rBodyHost);
    rLay->addWidget(m_resultTitle);
    rLay->addWidget(m_resultScroll, 1);

    m_btnAnalyze = new QPushButton(QStringLiteral("AI 判定今日达标"), card);
    m_btnAnalyze->setObjectName(QStringLiteral("SecondaryBtn"));

    m_toast = new QLabel(card);
    m_toast->setObjectName(QStringLiteral("ToastLabel"));
    m_toast->setWordWrap(true);

    lay->addWidget(m_checkinTitle);
    lay->addWidget(scroll, 1);
    lay->addWidget(m_btnAnalyze);
    lay->addWidget(m_resultCard);
    lay->addWidget(m_toast);

    connect(m_btnAnalyze, &QPushButton::clicked, this, &ExercisePage::onAnalyze);
    root->addWidget(card);
}

QFrame *ExercisePage::makeEmptyState(const QString &emoji, const QString &title,
                                     const QString &sub)
{
    auto *frame = new QFrame(this);
    frame->setStyleSheet(QStringLiteral("QFrame{background:#FFFFFF;border:1px dashed #D5DCE3;"
                                        "border-radius:12px;}"));
    auto *lay = new QVBoxLayout(frame);
    lay->setContentsMargins(20, 22, 20, 22);
    lay->setSpacing(8);
    // 与生成后的计划卡一致：内容顶部对齐，下方留白
    auto *icon = new QLabel(emoji, frame);
    icon->setAlignment(Qt::AlignLeft | Qt::AlignVCenter);
    icon->setStyleSheet(QStringLiteral("border:none;font-size:32px;"));
    auto *t = new QLabel(title, frame);
    t->setAlignment(Qt::AlignLeft | Qt::AlignVCenter);
    t->setStyleSheet(QStringLiteral("border:none;font-size:15px;font-weight:600;color:#22303F;"));
    auto *s = new QLabel(sub, frame);
    s->setAlignment(Qt::AlignLeft | Qt::AlignTop);
    s->setWordWrap(true);
    s->setStyleSheet(QStringLiteral("border:none;font-size:12px;color:#8A99A9;line-height:18px;"));

    lay->addWidget(icon);
    lay->addWidget(t);
    lay->addWidget(s);
    lay->addStretch(1);
    return frame;
}

void ExercisePage::onGenerate()
{
    if (m_busy) return;
    const QString goal = m_goalCombo->currentText();
    if (goal.isEmpty()) {
        showToast(QStringLiteral("请先选择目标"));
        return;
    }
    QStringList sports;
    QJsonObject ratios;
    int sum = 0;
    for (const auto &r : m_rows) {
        if (r.selected) {
            sports << r.name;
            ratios.insert(r.name, r.ratio);
            sum += r.ratio;
        }
    }
    if (sports.isEmpty()) {
        showToast(QStringLiteral("请至少点击选择一项运动"));
        return;
    }
    if (sum != 100) {
        showToast(QStringLiteral("运动占比总和需为 100%（当前 %1%）").arg(sum));
        return;
    }
    m_busy = true;
    m_btnGenerate->setEnabled(false);
    m_btnGenerate->setText(QStringLiteral("AI 生成中…"));
    showToast(QStringLiteral("正在根据今日饮食生成计划…"));
    ExerciseService::instance().generatePlan(g_currentUserId, goal, sports, ratios);
}

void ExercisePage::onConfirm()
{
    if (m_plan.planId <= 0) return;
    ExerciseService::instance().confirmPlan(m_plan.planId);
}

void ExercisePage::onCheckin(int taskIndex, bool completed)
{
    if (taskIndex < 0 || taskIndex >= m_plan.tasks.size()) return;
    const ExerciseTask &t = m_plan.tasks[taskIndex];
    if (t.checkinId <= 0) return;
    showToast(completed ? QStringLiteral("✓ 已完成「%1」").arg(t.title)
                        : QStringLiteral("已取消「%1」").arg(t.title));
    ExerciseService::instance().setCheckin(t.checkinId, completed);
}

void ExercisePage::onAnalyze()
{
    if (m_plan.planId <= 0 || m_plan.status != QLatin1String("confirmed")) {
        showToast(QStringLiteral("请先生成并确认今日计划"));
        return;
    }
    showToast(QStringLiteral("AI 判定中…"));
    ExerciseService::instance().analyzeDay(g_currentUserId, m_plan.planId, m_today);
}

void ExercisePage::renderPlan(const ExercisePlan &plan)
{
    m_middleEmpty->setVisible(plan.planId <= 0);
    m_summary->setVisible(plan.planId > 0);
    m_planTitle->setVisible(plan.planId > 0);
    m_cardsScroll->setVisible(plan.planId > 0);

    if (plan.planId <= 0) {
        m_planTitle->setText(QStringLiteral("今日运动计划"));
        m_summary->clear();
        m_btnConfirm->setVisible(false);
        m_taskCards.clear();
        return;
    }

    m_planTitle->setText(QStringLiteral("%1 · 目标：%2%3")
                             .arg(plan.planDate, plan.goal,
                                  plan.status == QLatin1String("confirmed")
                                      ? QStringLiteral(" · 已确认")
                                      : QStringLiteral(" · 待确认")));
    m_summary->setText(QStringLiteral("💡 %1").arg(plan.summary));
    if (plan.status == QLatin1String("pending")) {
        m_btnConfirm->setVisible(true);
        m_btnConfirm->setEnabled(true);
        m_btnConfirm->setText(QStringLiteral("确认计划，生成打卡清单"));
        m_btnConfirm->setStyleSheet(QString());   // 恢复 PrimaryBtn 主题样式
    } else {
        // 已确认：按钮不消失，白底灰字，不可再按
        m_btnConfirm->setVisible(true);
        m_btnConfirm->setEnabled(false);
        m_btnConfirm->setText(QStringLiteral("✓ 已生成清单"));
        m_btnConfirm->setStyleSheet(QStringLiteral(
            "QPushButton{background:#FFFFFF;color:#8A99A9;border:1px solid #E4E9EE;"
            "border-radius:8px;padding:8px 16px;font-weight:600;}"));
    }
    renderTaskCards();
}

// 单卡展示：每张卡 = 一个任务，信息完全展示，多任务滑动切换
void ExercisePage::renderTaskCards()
{
    // 安全清理旧卡：统一 deleteLater，避免双删
    while (m_cardsLay->count()) {
        QLayoutItem *it = m_cardsLay->takeAt(0);
        if (QWidget *w = it->widget()) w->deleteLater();
        delete it;
    }
    m_taskCards.clear();
    m_cardIndex = 0;
    if (m_slideAnim) {
        m_slideAnim->stop();
        m_slideAnim->deleteLater();
        m_slideAnim = nullptr;
    }

    for (int i = 0; i < m_plan.tasks.size(); ++i)
        m_taskCards.append(makeTaskCard(m_plan.tasks[i], i));

    const int n = m_taskCards.size();
    m_btnPrev->setEnabled(n > 1);
    m_btnNext->setEnabled(n > 1);
    m_pageLabel->setText(QStringLiteral("1/%1").arg(n));

    for (QFrame *c : m_taskCards)
        m_cardsLay->addWidget(c);

    resizeCards();
    m_cardsHost->move(0, 0);
}

QFrame *ExercisePage::makeTaskCard(const ExerciseTask &task, int idx)
{
    auto *card = new QFrame(m_cardsHost);
    card->setObjectName(QStringLiteral("TaskCard"));
    card->setStyleSheet(QStringLiteral(
        "QFrame#TaskCard{background:#FFFFFF;border:1px solid #E4E9EE;border-radius:12px;}"));

    auto *lay = new QVBoxLayout(card);
    lay->setContentsMargins(16, 12, 16, 10);
    lay->setSpacing(6);

    // 第一行：序号 + 运动 + 标题
    auto *head = new QHBoxLayout;
    head->setSpacing(8);
    auto *seq = new QLabel(QStringLiteral("%1").arg(idx + 1), card);
    seq->setAlignment(Qt::AlignCenter);
    seq->setFixedSize(26, 26);
    seq->setStyleSheet(QStringLiteral(
        "background:#EAF6F0;color:#1F7A52;border-radius:13px;font-size:13px;font-weight:700;"));
    auto *title = new QLabel(
        QStringLiteral("<b>%1</b>　%2").arg(task.sportType, task.title), card);
    title->setStyleSheet(QStringLiteral("border:none;color:#22303F;font-size:15px;"));
    head->addWidget(seq);
    head->addWidget(title, 1);
    lay->addLayout(head);

    // 摘要行
    QString sub;
    if (task.durationMin > 0) sub += QStringLiteral("%1 分钟").arg(task.durationMin);
    if (task.distanceKm > 0)  sub += QStringLiteral(" · %1 km").arg(task.distanceKm, 0, 'f', 1);
    if (task.calories > 0)    sub += QStringLiteral(" · 约 %1 kcal").arg(task.calories);
    auto *subLabel = new QLabel(sub, card);
    subLabel->setStyleSheet(QStringLiteral("border:none;color:#1F7A52;font-size:13px;font-weight:600;"));
    lay->addWidget(subLabel);

    // 详情：内容 + 时长/距离/热量建议（完全展示，与主题同色不加深）
    auto *detail = new QFrame(card);
    detail->setStyleSheet(QStringLiteral("QFrame{background:#FFFFFF;"
                                         "border-radius:10px;border:1px solid #E4E9EE;}"));
    auto *dLay = new QVBoxLayout(detail);
    dLay->setContentsMargins(12, 8, 12, 8);
    dLay->setSpacing(4);
    if (!task.content.isEmpty()) {
        auto *l1 = new QLabel(QStringLiteral("▸ %1").arg(task.content), detail);
        l1->setWordWrap(true);
        l1->setStyleSheet(QStringLiteral("border:none;color:#33424F;font-size:12px;"));
        dLay->addWidget(l1);
    }
    auto *l2 = new QLabel(
        QStringLiteral("▸ 推荐时长 %1 分钟%2，预计消耗 %3 kcal")
            .arg(task.durationMin)
            .arg(task.distanceKm > 0
                     ? QStringLiteral("，距离约 %1 km").arg(task.distanceKm, 0, 'f', 1)
                     : QStringLiteral(""))
            .arg(task.calories),
        detail);
    l2->setWordWrap(true);
    l2->setStyleSheet(QStringLiteral("border:none;color:#33424F;font-size:12px;"));
    dLay->addWidget(l2);
    lay->addWidget(detail);
    lay->addStretch(1);
    return card;
}

void ExercisePage::showCard(int idx)
{
    if (idx < 0 || idx >= m_taskCards.size()) return;
    if (idx == m_cardIndex) return;
    m_cardIndex = idx;
    const int w = qMax(40, m_cardsScroll->viewport()->width());
    const int targetX = -idx * w;
    const int curX = m_cardsHost->pos().x();
    // 停止旧动画并安全清理（防止悬垂指针）
    if (m_slideAnim) {
        m_slideAnim->stop();
        m_slideAnim->deleteLater();
        m_slideAnim = nullptr;
    }
    auto *anim = new QPropertyAnimation(m_cardsHost, "pos", this);
    m_slideAnim = anim;
    anim->setDuration(280);
    anim->setEasingCurve(QEasingCurve::OutCubic);
    anim->setStartValue(QPoint(curX, 0));
    anim->setEndValue(QPoint(targetX, 0));
    connect(anim, &QPropertyAnimation::finished, this, [this, anim]() {
        if (m_slideAnim == anim) m_slideAnim = nullptr;
        anim->deleteLater();
    });
    anim->start();
    m_pageLabel->setText(QStringLiteral("%1/%2").arg(idx + 1).arg(m_taskCards.size()));
}

void ExercisePage::resizeCards()
{
    if (m_taskCards.isEmpty() || !m_cardsScroll->isVisible()) return;
    const int w = qMax(40, m_cardsScroll->viewport()->width());
    const int h = qMax(120, m_cardsScroll->viewport()->height());
    // 计划卡片撑满卡片区（恢复原样式）
    for (int i = 0; i < m_taskCards.size(); ++i)
        m_taskCards[i]->setFixedSize(w, h);
    m_cardsHost->resize(w * m_taskCards.size(), h);
    // 校正位置（切页时保持当前页）
    m_cardsHost->move(-m_cardIndex * w, 0);
}

void ExercisePage::resizeEvent(QResizeEvent *ev)
{
    QWidget::resizeEvent(ev);
    resizeCards();
    layoutCheckins();
}

QFrame *ExercisePage::makeTaskRow(const ExerciseTask &task, bool editable)
{
    auto *row = new QFrame(this);
    row->setObjectName(QStringLiteral("SportTaskCard"));
    row->setFixedHeight(kTaskRowHeight);
    row->setStyleSheet(QStringLiteral("QFrame#SportTaskCard{background:#FFFFFF;"
                                      "border:1px solid #E4E9EE;border-radius:12px;}"));
    auto *lay = new QHBoxLayout(row);
    lay->setContentsMargins(14, 10, 14, 10);
    lay->setSpacing(10);

    // 两行固定排版：第一行运动·标题，第二行内容·时长·距离·热量
    QString line1 = QStringLiteral("%1 · %2").arg(task.sportType, task.title);
    QString line2 = task.content;
    if (task.durationMin > 0)
        line2 += QStringLiteral(" · %1分钟").arg(task.durationMin);
    if (task.distanceKm > 0)
        line2 += QStringLiteral(" · %1km").arg(task.distanceKm, 0, 'f', 1);
    if (task.calories > 0)
        line2 += QStringLiteral(" · ≈%1 kcal").arg(task.calories);

    auto *info = new QLabel(
        QStringLiteral("<b>%1</b><br><span style='color:#5C6F82;'>%2</span>")
            .arg(elide(line1, 18), elide(line2, 34)),
        row);
    info->setWordWrap(true);
    info->setAlignment(Qt::AlignVCenter | Qt::AlignLeft);
    info->setStyleSheet(QStringLiteral("border:none;color:#22303F;font-size:14px;"));
    lay->addWidget(info, 1);

    if (editable) {
        auto *btn = new QPushButton(task.completed ? QStringLiteral("已完成 ✓")
                                                  : QStringLiteral("完成"),
                                    row);
        btn->setCursor(Qt::PointingHandCursor);
        btn->setFixedWidth(84);
        btn->setFixedHeight(34);
        btn->setStyleSheet(task.completed
            ? QStringLiteral("QPushButton{background:#EAF6F0;color:#1F7A52;border:1px solid #BFE3D0;"
                             "border-radius:8px;font-size:13px;font-weight:600;}")
            : QStringLiteral("QPushButton{background:#2E9E6B;color:white;border:none;"
                             "border-radius:8px;font-size:13px;font-weight:600;}"));
        connect(btn, &QPushButton::clicked, this, [this, btn, task]() {
            onCheckin(btn->property("taskIndex").toInt(), !task.completed);
        });
        lay->addWidget(btn, 0, Qt::AlignVCenter);
    } else {
        auto *badge = new QLabel(
            task.calories > 0 ? QStringLiteral("≈%1\nkcal").arg(task.calories)
                              : QStringLiteral(""),
            row);
        badge->setAlignment(Qt::AlignCenter);
        badge->setStyleSheet(QStringLiteral("color:#8A99A9;font-size:11px;border:none;"));
        lay->addWidget(badge, 0, Qt::AlignVCenter);
    }
    return row;
}

void ExercisePage::renderCheckinList(const ExercisePlan &plan)
{
    // 同步清理旧卡（立即 delete，避免 deleteLater 残留占位）
    while (m_checkinLay->count()) {
        QLayoutItem *it = m_checkinLay->takeAt(0);
        QWidget *w = it->widget();
        if (w) {
            w->hide();
            w->deleteLater();
        }
        delete it;
    }
    m_checkinRows.clear();

    if (plan.status != QLatin1String("confirmed") || plan.tasks.isEmpty()) {
        auto *empty = makeEmptyState(
            QStringLiteral("📋"),
            QStringLiteral("暂无打卡任务"),
            QStringLiteral("确认今日计划后，打卡清单会显示在这里\n每项只需点「完成」即可"));
        m_checkinLay->addWidget(empty);
        m_checkinRows.append(empty);
        m_checkinTitle->setText(QStringLiteral("今日打卡清单"));
        // 未确认：达标卡灰度
        m_resultTitle->setText(QStringLiteral("待判定"));
        m_resultBody->setText(QStringLiteral("确认计划并打卡后，可点击下方按钮让 AI 判定今日是否达标"));
        layoutCheckins();
        return;
    }
    m_checkinTitle->setText(QStringLiteral("今日打卡清单 · %1 项").arg(plan.tasks.size()));
    for (int i = 0; i < plan.tasks.size(); ++i) {
        QFrame *row = makeTaskRow(plan.tasks[i], true);
        for (QPushButton *b : row->findChildren<QPushButton *>())
            b->setProperty("taskIndex", i);
        m_checkinLay->addWidget(row);
        m_checkinRows.append(row);
    }
    layoutCheckins();
}

// 任务卡均分铺满排列区：1张=全高，2张=各1/2，3张=各1/3
void ExercisePage::layoutCheckins()
{
    if (m_checkinRows.isEmpty() || !m_checkinScroll) return;
    const int w = qMax(40, m_checkinScroll->viewport()->width() - 20);
    const int h = qMax(120, m_checkinScroll->viewport()->height() - 20);
    const int n = m_checkinRows.size();
    const int gap = 8;
    const int cardH = qMax(70, (h - gap * (n - 1)) / n);
    for (QFrame *r : m_checkinRows)
        r->setFixedSize(w, cardH);
    if (m_checkinHost)
        m_checkinHost->setMinimumHeight(h);
}

void ExercisePage::renderDayResult(bool met, int done, int total,
                                   const QStringList &reasons,
                                   const QString &advice,
                                   double todayCal, double targetCal)
{
    if (met) {
        m_resultCard->setStyleSheet(QStringLiteral(
            "QFrame{background:#E7F5EE;border-radius:12px;border:1px solid #2E9E6B;}"));
        m_resultTitle->setText(QStringLiteral("已达标 ✓"));
        m_resultTitle->setStyleSheet(QStringLiteral(
            "border:none;font-size:16px;font-weight:700;color:#1F7A52;"));
        m_resultBody->setStyleSheet(QStringLiteral(
            "border:none;font-size:12px;color:#1F7A52;"));
        m_resultBody->setText(QStringLiteral("今日 %1 项运动全部完成，计划达成！\n今日摄入 %2 / 目标 %3 kcal%4")
                                  .arg(total)
                                  .arg(qRound(todayCal)).arg(qRound(targetCal))
                                  .arg(advice.isEmpty() ? QStringLiteral("")
                                                        : QStringLiteral("\n\n教练建议：%1").arg(advice)));
        showToast(QStringLiteral("🎉 已达标！今日 %1 项运动全部完成").arg(total));
    } else {
        m_resultCard->setStyleSheet(QStringLiteral(
            "QFrame{background:#FFFFFF;border-radius:12px;border:1px solid #E4E9EE;}"));
        m_resultTitle->setText(QStringLiteral("未达标"));
        m_resultTitle->setStyleSheet(QStringLiteral(
            "border:none;font-size:16px;font-weight:700;color:#8A99A9;"));
        m_resultBody->setStyleSheet(QStringLiteral(
            "border:none;font-size:12px;color:#8A99A9;"));
        QString body = QStringLiteral("打卡进度：%1 / %2 · 今日摄入 %3 / 目标 %4 kcal")
                           .arg(done).arg(total)
                           .arg(qRound(todayCal)).arg(qRound(targetCal));
        if (!reasons.isEmpty())
            body += QStringLiteral("\n") + reasons.join('\n');
        if (!advice.isEmpty())
            body += QStringLiteral("\n\n教练建议：%1").arg(advice);
        m_resultBody->setText(body);
        showToast(QStringLiteral("未达标：打卡 %1 / %2，继续加油").arg(done).arg(total));
    }
}

void ExercisePage::showToast(const QString &msg)
{
    if (m_toast)
        m_toast->setText(msg);
}
