#include "RecordsPage.h"

#include <QComboBox>
#include <QDateEdit>
#include <QDateTime>
#include <QHBoxLayout>
#include <QHeaderView>
#include <QLabel>
#include <QMessageBox>
#include <QPushButton>
#include <QTableWidget>
#include <QTimer>
#include <QVBoxLayout>

#include "../config.h"
#include "../services/NutritionService.h"
#include "../services/ProfileService.h"
#include "../services/RecordService.h"
#include "../widgets/FoodPickerDialog.h"
#include "../widgets/MetricCard.h"

namespace {
const QColor kGreen(0x2E, 0x9E, 0x6B), kBlue(0x3B, 0x82, 0xF6),
             kOrange(0xF5, 0xA6, 0x23), kPurple(0x8E, 0x6F, 0xD8);
}

RecordsPage::RecordsPage(QWidget *parent)
    : QWidget(parent)
{
    auto *root = new QVBoxLayout(this);
    root->setContentsMargins(24, 20, 24, 16);
    root->setSpacing(14);

    auto *header = new QHBoxLayout;
    auto *titleBox = new QVBoxLayout;
    auto *title = new QLabel(QStringLiteral("饮食记录"), this);
    title->setObjectName(QStringLiteral("PageTitle"));
    auto *subtitle = new QLabel(QStringLiteral("按日期查看每餐摄入，支持添加、编辑与删除"), this);
    subtitle->setObjectName(QStringLiteral("PageSubtitle"));
    titleBox->addWidget(title);
    titleBox->addWidget(subtitle);
    header->addLayout(titleBox);
    header->addStretch(1);

    auto *prev = new QPushButton(QStringLiteral("◀"), this);
    prev->setObjectName(QStringLiteral("GhostBtn"));
    prev->setFixedWidth(36);
    auto *next = new QPushButton(QStringLiteral("▶"), this);
    next->setObjectName(QStringLiteral("GhostBtn"));
    next->setFixedWidth(36);
    m_dateEdit = new QDateEdit(QDate::currentDate(), this);
    m_dateEdit->setCalendarPopup(true);
    m_dateEdit->setDisplayFormat(QStringLiteral("yyyy-MM-dd"));
    m_dateEdit->setFixedWidth(130);
    auto *today = new QPushButton(QStringLiteral("今天"), this);
    today->setObjectName(QStringLiteral("GhostBtn"));

    m_mealFilter = new QComboBox(this);
    m_mealFilter->addItems({QStringLiteral("全部餐次"), QStringLiteral("早餐"),
                            QStringLiteral("午餐"), QStringLiteral("晚餐"), QStringLiteral("加餐")});

    auto *add = new QPushButton(QStringLiteral("＋ 添加记录"), this);
    add->setObjectName(QStringLiteral("PrimaryBtn"));

    header->addWidget(prev);
    header->addWidget(m_dateEdit);
    header->addWidget(next);
    header->addWidget(today);
    header->addSpacing(12);
    header->addWidget(m_mealFilter);
    header->addSpacing(8);
    header->addWidget(add);
    root->addLayout(header);

    root->addWidget(buildSummaryRow());

    m_table = new QTableWidget(this);
    m_table->setColumnCount(9);
    m_table->setHorizontalHeaderLabels({
        QStringLiteral("时间"), QStringLiteral("餐次"), QStringLiteral("菜品"),
        QStringLiteral("份量(g)"), QStringLiteral("热量(kcal)"), QStringLiteral("蛋白质(g)"),
        QStringLiteral("脂肪(g)"), QStringLiteral("碳水(g)"), QStringLiteral("操作")
    });
    m_table->horizontalHeader()->setSectionResizeMode(QHeaderView::Stretch);
    m_table->horizontalHeader()->setSectionResizeMode(0, QHeaderView::ResizeToContents);
    m_table->horizontalHeader()->setSectionResizeMode(1, QHeaderView::ResizeToContents);
    m_table->horizontalHeader()->setSectionResizeMode(8, QHeaderView::Fixed);
    m_table->setColumnWidth(8, 130);
    m_table->verticalHeader()->setVisible(false);
    m_table->setSelectionBehavior(QAbstractItemView::SelectRows);
    m_table->setSelectionMode(QAbstractItemView::SingleSelection);
    m_table->setEditTriggers(QAbstractItemView::NoEditTriggers);
    m_table->setAlternatingRowColors(true);
    m_table->setShowGrid(false);
    m_table->verticalHeader()->setDefaultSectionSize(44);
    root->addWidget(m_table, 1);

    m_toast = new QLabel(this);
    m_toast->setObjectName(QStringLiteral("ToastLabel"));
    root->addWidget(m_toast);

    connect(prev, &QPushButton::clicked, this, &RecordsPage::onPrevDay);
    connect(next, &QPushButton::clicked, this, &RecordsPage::onNextDay);
    connect(today, &QPushButton::clicked, this, &RecordsPage::onToday);
    connect(m_dateEdit, &QDateEdit::dateChanged, this, [this]() { refresh(); });
    connect(m_mealFilter, &QComboBox::currentTextChanged, this, [this]() { reloadTable(); });
    connect(add, &QPushButton::clicked, this, &RecordsPage::onAddRecord);

    // 连接 RecordService 信号
    RecordService &rs = RecordService::instance();
    connect(&rs, &RecordService::recordsLoaded, this, &RecordsPage::onRecordsLoaded);
    connect(&rs, &RecordService::recordAdded, this, &RecordsPage::onRecordAdded);
    connect(&rs, &RecordService::recordUpdated, this, &RecordsPage::onRecordUpdated);
    connect(&rs, &RecordService::recordDeleted, this, &RecordsPage::onRecordDeleted);
    connect(&rs, &RecordService::error, this, &RecordsPage::onError);

    refresh();
}

QWidget *RecordsPage::buildSummaryRow()
{
    auto *row = new QWidget(this);
    auto *lay = new QHBoxLayout(row);
    lay->setContentsMargins(0, 0, 0, 0);
    lay->setSpacing(12);

    m_cardCal = new MetricCard(row);
    m_cardProtein = new MetricCard(row);
    m_cardFat = new MetricCard(row);
    m_cardCarb = new MetricCard(row);

    lay->addWidget(m_cardCal);
    lay->addWidget(m_cardProtein);
    lay->addWidget(m_cardFat);
    lay->addWidget(m_cardCarb);
    return row;
}

QDate RecordsPage::currentDate() const
{
    return m_dateEdit->date();
}

void RecordsPage::refresh()
{
    RecordService::instance().loadDate(currentDate());
}

void RecordsPage::onRecordsLoaded(const QDate &date, const QVector<MealRecord> &records)
{
    if (date != currentDate())
        return;
    m_records = records;
    updateSummary();
    reloadTable();
}

void RecordsPage::updateSummary()
{
    double cal = 0, protein = 0, fat = 0, carb = 0;
    for (const MealRecord &r : m_records) {
        cal += r.amount.cal;
        protein += r.amount.protein;
        fat += r.amount.fat;
        carb += r.amount.carb;
    }
    const double targetCal = ProfileService::instance().targetCalorie();
    const double targetProtein = AppConfig::kDefaultTargetProtein;
    const double targetFat = AppConfig::kDefaultTargetFat;
    const double targetCarb = AppConfig::kDefaultTargetCarb;

    const double calPct = targetCal > 0 ? cal / targetCal : 0.0;
    m_cardCal->setMetric(QStringLiteral("当日热量"),
                         QStringLiteral("%1 / %2").arg(qRound(cal)).arg(qRound(targetCal)),
                         QStringLiteral("kcal · 目标"),
                         calPct, calPct > 1.0 ? kOrange : kGreen);
    m_cardProtein->setMetric(QStringLiteral("蛋白质"),
                             QStringLiteral("%1 / %2").arg(qRound(protein)).arg(qRound(targetProtein)),
                             QStringLiteral("g · 目标"),
                             targetProtein > 0 ? protein / targetProtein : 0.0, kBlue);
    m_cardFat->setMetric(QStringLiteral("脂肪"),
                         QStringLiteral("%1 / %2").arg(qRound(fat)).arg(qRound(targetFat)),
                         QStringLiteral("g · 目标"),
                         targetFat > 0 ? fat / targetFat : 0.0, kOrange);
    m_cardCarb->setMetric(QStringLiteral("碳水"),
                          QStringLiteral("%1 / %2").arg(qRound(carb)).arg(qRound(targetCarb)),
                          QStringLiteral("g · 目标"),
                          targetCarb > 0 ? carb / targetCarb : 0.0, kPurple);
}

void RecordsPage::reloadTable()
{
    m_table->setRowCount(0);
    const QString filter = m_mealFilter->currentText();

    int row = 0;
    for (const MealRecord &r : m_records) {
        if (filter != QStringLiteral("全部餐次") && r.mealType != filter)
            continue;

        m_table->insertRow(row);
        const auto setCell = [&](int col, const QString &text) {
            auto *item = new QTableWidgetItem(text);
            item->setTextAlignment(Qt::AlignCenter);
            if (col >= 1 && col <= 7)
                item->setForeground(col == 1 ? QColor(0x1F, 0x7A, 0x52) : QColor(0x22, 0x30, 0x3F));
            m_table->setItem(row, col, item);
        };

        setCell(0, r.eatenAt.toString(QStringLiteral("HH:mm")));
        setCell(1, r.mealType);
        setCell(2, r.foodName);
        setCell(3, QString::number(qRound(r.portionG)));
        setCell(4, QString::number(qRound(r.amount.cal)));
        setCell(5, QString::number(r.amount.protein, 'f', 1));
        setCell(6, QString::number(r.amount.fat, 'f', 1));
        setCell(7, QString::number(r.amount.carb, 'f', 1));

        auto *op = new QWidget(m_table);
        auto *opLay = new QHBoxLayout(op);
        opLay->setContentsMargins(4, 2, 4, 2);
        opLay->setSpacing(6);
        auto *editBtn = new QPushButton(QStringLiteral("编辑"), op);
        editBtn->setObjectName(QStringLiteral("GhostBtn"));
        editBtn->setFixedWidth(52);
        editBtn->setStyleSheet(QStringLiteral(
            "QPushButton{background:#fff;color:#5A6B7C;border:1px solid #D5DDE5;border-radius:6px;"
            "padding:4px 0px;font-size:12px;}"
            "QPushButton:hover{background:#EEF1F4;}"));
        editBtn->setProperty("rid", r.id);
        auto *delBtn = new QPushButton(QStringLiteral("删除"), op);
        delBtn->setObjectName(QStringLiteral("DangerBtn"));
        delBtn->setFixedWidth(52);
        delBtn->setStyleSheet(QStringLiteral(
            "QPushButton{background:#fff;color:#E5484D;border:1px solid #E5484D;border-radius:6px;"
            "padding:4px 0px;font-size:12px;}"
            "QPushButton:hover{background:#FDEDEE;}"));
        delBtn->setProperty("rid", r.id);
        opLay->addWidget(editBtn);
        opLay->addWidget(delBtn);
        m_table->setCellWidget(row, 8, op);

        connect(editBtn, &QPushButton::clicked, this, &RecordsPage::onEditRecord);
        connect(delBtn, &QPushButton::clicked, this, &RecordsPage::onDeleteRecord);
        ++row;
    }
}

void RecordsPage::onPrevDay()
{
    m_dateEdit->setDate(currentDate().addDays(-1));
}

void RecordsPage::onNextDay()
{
    m_dateEdit->setDate(currentDate().addDays(1));
}

void RecordsPage::onToday()
{
    m_dateEdit->setDate(QDate::currentDate());
}

void RecordsPage::onAddRecord()
{
    FoodPickerDialog dlg(this);
    dlg.setWindowTitle(QStringLiteral("手动添加记录"));
    dlg.setRecordFields(true, nullptr);

    if (dlg.exec() != QDialog::Accepted)
        return;
    const QString name = dlg.selectedFood();
    if (name.isEmpty())
        return;

    const FoodItem *f = NutritionService::instance().findByName(name);
    if (!f) {
        QMessageBox::warning(this, QStringLiteral("提示"), QStringLiteral("选择的食物不在库中"));
        return;
    }

    RecordService::instance().addRecord(
        f->id, dlg.mealType(), dlg.portionG(), dlg.eatenAt());
}

void RecordsPage::onRecordAdded(const MealRecord &record)
{
    m_toast->setText(QStringLiteral("✓ 已添加：%1 · %2").arg(record.foodName, record.mealType));
    QTimer::singleShot(4000, this, [this]() { m_toast->clear(); });
    refresh();
}

void RecordsPage::onEditRecord()
{
    auto *btn = qobject_cast<QPushButton *>(sender());
    if (!btn)
        return;
    const int rid = btn->property("rid").toInt();

    const MealRecord *target = nullptr;
    for (const MealRecord &r : m_records)
        if (r.id == rid) { target = &r; break; }
    if (!target)
        return;

    FoodPickerDialog dlg(this);
    dlg.setWindowTitle(QStringLiteral("编辑记录"));
    dlg.setRecordFields(true, target);

    if (dlg.exec() != QDialog::Accepted)
        return;

    // 后端只支持更新份量
    RecordService::instance().updateRecord(rid, dlg.portionG());
}

void RecordsPage::onRecordUpdated(int id)
{
    Q_UNUSED(id);
    m_toast->setText(QStringLiteral("✓ 已更新记录"));
    QTimer::singleShot(4000, this, [this]() { m_toast->clear(); });
    refresh();
}

void RecordsPage::onDeleteRecord()
{
    auto *btn = qobject_cast<QPushButton *>(sender());
    if (!btn)
        return;
    const int rid = btn->property("rid").toInt();

    if (QMessageBox::question(this, QStringLiteral("确认删除"),
                              QStringLiteral("确定删除这条饮食记录吗？"),
                              QMessageBox::Yes | QMessageBox::No) != QMessageBox::Yes)
        return;

    RecordService::instance().deleteRecord(rid);
}

void RecordsPage::onRecordDeleted(int id)
{
    Q_UNUSED(id);
    m_toast->setText(QStringLiteral("已删除该记录"));
    QTimer::singleShot(4000, this, [this]() { m_toast->clear(); });
    refresh();
}

void RecordsPage::onError(const QString &msg)
{
    m_toast->setText(QStringLiteral("⚠ %1").arg(msg));
    m_toast->setStyleSheet(QStringLiteral("color:#E5484D;"));
    QTimer::singleShot(5000, this, [this]() { m_toast->clear(); m_toast->setStyleSheet(QString()); });
}
