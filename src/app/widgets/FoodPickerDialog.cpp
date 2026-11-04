#include "FoodPickerDialog.h"

#include <QComboBox>
#include <QDateTimeEdit>
#include <QDialogButtonBox>
#include <QDoubleSpinBox>
#include <QFormLayout>
#include <QHBoxLayout>
#include <QLineEdit>
#include <QListWidget>
#include <QLabel>
#include <QPushButton>
#include <QVBoxLayout>

#include "../config.h"
#include "../models/MealRecord.h"
#include "../services/NutritionService.h"

FoodPickerDialog::FoodPickerDialog(QWidget *parent)
    : QDialog(parent)
{
    setWindowTitle(QStringLiteral("选择食物"));
    setModal(true);
    setMinimumSize(460, 480);

    m_search = new QLineEdit(this);
    m_search->setPlaceholderText(QStringLiteral("输入食物/菜品名称或分类，如：鸡、米饭、蔬菜"));

    m_list = new QListWidget(this);
    m_list->setObjectName(QStringLiteral("FoodList"));
    m_list->setSelectionMode(QAbstractItemView::SingleSelection);

    // 记录字段（默认隐藏）
    m_portion = new QDoubleSpinBox(this);
    m_portion->setRange(10.0, 3000.0);
    m_portion->setSingleStep(10.0);
    m_portion->setSuffix(QStringLiteral(" 克"));
    m_portion->setValue(150.0);

    m_meal = new QComboBox(this);
    m_meal->addItems(AppConfig::kMealTypes);

    m_time = new QDateTimeEdit(QDateTime::currentDateTime(), this);
    m_time->setCalendarPopup(true);
    m_time->setDisplayFormat(QStringLiteral("yyyy-MM-dd HH:mm"));

    auto *recordForm = new QFormLayout;
    recordForm->addRow(QStringLiteral("份量"), m_portion);
    recordForm->addRow(QStringLiteral("餐次"), m_meal);
    recordForm->addRow(QStringLiteral("时间"), m_time);

    auto *buttons = new QDialogButtonBox(QDialogButtonBox::Ok | QDialogButtonBox::Cancel, this);
    m_ok = buttons->button(QDialogButtonBox::Ok);
    m_ok->setText(QStringLiteral("确定"));
    m_ok->setObjectName(QStringLiteral("PrimaryBtn"));
    m_ok->setEnabled(false);
    auto *cancel = buttons->button(QDialogButtonBox::Cancel);
    cancel->setText(QStringLiteral("取消"));
    cancel->setObjectName(QStringLiteral("GhostBtn"));

    auto *lay = new QVBoxLayout(this);
    lay->setContentsMargins(20, 20, 20, 16);
    lay->setSpacing(12);
    lay->addWidget(m_search);
    lay->addWidget(m_list, 1);
    lay->addLayout(recordForm);
    lay->addWidget(buttons);

    m_portion->hide();
    m_meal->hide();
    m_time->hide();

    connect(m_search, &QLineEdit::textChanged, this, &FoodPickerDialog::onSearchChanged);
    connect(m_list, &QListWidget::itemDoubleClicked, this, &FoodPickerDialog::onListDoubleClicked);
    connect(m_list, &QListWidget::itemSelectionChanged, this, &FoodPickerDialog::updateOkState);
    connect(buttons, &QDialogButtonBox::accepted, this, &QDialog::accept);
    connect(buttons, &QDialogButtonBox::rejected, this, &QDialog::reject);

    refreshList();
}

void FoodPickerDialog::setOriginalName(const QString &name)
{
    m_search->setText(name);
}

void FoodPickerDialog::setRecordFields(bool enable, const MealRecord *prefill)
{
    m_recordFields = enable;
    m_portion->setVisible(enable);
    m_meal->setVisible(enable);
    m_time->setVisible(enable);
    if (prefill) {
        m_portion->setValue(prefill->portionG);
        m_meal->setCurrentText(prefill->mealType);
        m_time->setDateTime(prefill->eatenAt);
        m_search->setText(prefill->foodName);
    }
    setMinimumHeight(enable ? 560 : 480);
}

void FoodPickerDialog::onSearchChanged()
{
    refreshList();
}

void FoodPickerDialog::refreshList()
{
    m_list->clear();
    const auto foods = NutritionService::instance().searchFoods(m_search->text());
    for (const FoodItem &f : foods) {
        auto *item = new QListWidgetItem(
            QStringLiteral("%1  ·  %2  ·  %3/100g")
                .arg(f.name, f.category, NutritionService::formatKcal(f.per100g.cal)),
            m_list);
        item->setData(Qt::UserRole, f.name);
    }
    updateOkState();
}

void FoodPickerDialog::updateOkState()
{
    const bool has = m_list->currentItem() != nullptr;
    m_ok->setEnabled(has);
}

void FoodPickerDialog::onListDoubleClicked()
{
    if (m_list->currentItem())
        accept();
}

QString FoodPickerDialog::selectedFood() const
{
    auto *item = m_list->currentItem();
    return item ? item->data(Qt::UserRole).toString() : QString();
}

double FoodPickerDialog::portionG() const
{
    return m_portion->value();
}

QString FoodPickerDialog::mealType() const
{
    return m_meal->currentText();
}

QDateTime FoodPickerDialog::eatenAt() const
{
    return m_time->dateTime();
}
