#include "WeightRecordDialog.h"

#include <QDate>
#include <QDateEdit>
#include <QDialogButtonBox>
#include <QDoubleSpinBox>
#include <QFormLayout>
#include <QPushButton>
#include <QVBoxLayout>

WeightRecordDialog::WeightRecordDialog(QWidget *parent)
    : QDialog(parent)
{
    setWindowTitle(QStringLiteral("记录体重"));
    setModal(true);
    setMinimumWidth(320);

    m_weight = new QDoubleSpinBox(this);
    m_weight->setRange(20.0, 300.0);
    m_weight->setDecimals(1);
    m_weight->setSingleStep(0.5);
    m_weight->setSuffix(QStringLiteral(" kg"));
    m_weight->setValue(65.0);

    m_date = new QDateEdit(QDate::currentDate(), this);
    m_date->setCalendarPopup(true);
    m_date->setDisplayFormat(QStringLiteral("yyyy-MM-dd"));

    auto *form = new QFormLayout;
    form->setSpacing(14);
    form->addRow(QStringLiteral("体重"), m_weight);
    form->addRow(QStringLiteral("日期"), m_date);

    auto *buttons = new QDialogButtonBox(QDialogButtonBox::Ok | QDialogButtonBox::Cancel, this);
    buttons->button(QDialogButtonBox::Ok)->setText(QStringLiteral("保存"));
    buttons->button(QDialogButtonBox::Ok)->setObjectName(QStringLiteral("PrimaryBtn"));
    buttons->button(QDialogButtonBox::Cancel)->setText(QStringLiteral("取消"));
    buttons->button(QDialogButtonBox::Cancel)->setObjectName(QStringLiteral("GhostBtn"));

    auto *lay = new QVBoxLayout(this);
    lay->setContentsMargins(24, 24, 24, 18);
    lay->setSpacing(16);
    lay->addLayout(form);
    lay->addWidget(buttons);

    connect(buttons, &QDialogButtonBox::accepted, this, &QDialog::accept);
    connect(buttons, &QDialogButtonBox::rejected, this, &QDialog::reject);
}

double WeightRecordDialog::weightKg() const
{
    return m_weight->value();
}

QDate WeightRecordDialog::date() const
{
    return m_date->date();
}
