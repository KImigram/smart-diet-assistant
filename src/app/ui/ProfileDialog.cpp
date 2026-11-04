#include "ProfileDialog.h"

#include <QComboBox>
#include <QDate>
#include <QDialogButtonBox>
#include <QDoubleSpinBox>
#include <QFormLayout>
#include <QLabel>
#include <QLineEdit>
#include <QMessageBox>
#include <QPushButton>
#include <QSpinBox>
#include <QVBoxLayout>

#include "../config.h"
#include "../services/ProfileService.h"

ProfileDialog::ProfileDialog(QWidget *parent)
    : QDialog(parent)
{
    setWindowTitle(QStringLiteral("健康档案"));
    setModal(true);
    setMinimumWidth(420);

    m_nickname = new QLineEdit(this);
    m_gender = new QComboBox(this);
    m_gender->addItems({QStringLiteral("男"), QStringLiteral("女")});
    m_age = new QSpinBox(this);
    m_age->setRange(10, 100);
    m_height = new QDoubleSpinBox(this);
    m_height->setRange(100.0, 250.0);
    m_height->setSuffix(QStringLiteral(" cm"));
    m_weight = new QDoubleSpinBox(this);
    m_weight->setRange(30.0, 300.0);
    m_weight->setSuffix(QStringLiteral(" kg"));
    m_activity = new QComboBox(this);
    for (const auto &lv : AppConfig::kActivityLevels)
        m_activity->addItem(lv.name);

    m_targetCal = new QDoubleSpinBox(this);
    m_targetCal->setRange(800.0, 6000.0);
    m_targetCal->setSingleStep(50.0);
    m_targetCal->setSuffix(QStringLiteral(" kcal/天"));

    auto *estimateBtn = new QPushButton(QStringLiteral("按公式估算"), this);
    estimateBtn->setObjectName(QStringLiteral("LinkBtn"));

    m_allergens = new QLineEdit(this);
    m_allergens->setPlaceholderText(QStringLiteral("如：花生、海鲜，多个用逗号分隔"));

    auto *form = new QFormLayout;
    form->setSpacing(14);
    form->addRow(QStringLiteral("昵称"), m_nickname);
    form->addRow(QStringLiteral("性别"), m_gender);
    form->addRow(QStringLiteral("年龄"), m_age);
    form->addRow(QStringLiteral("身高"), m_height);
    form->addRow(QStringLiteral("体重"), m_weight);
    form->addRow(QStringLiteral("活动水平"), m_activity);
    form->addRow(QStringLiteral("每日目标热量"), m_targetCal);
    form->addRow(QString(), estimateBtn);
    form->addRow(QStringLiteral("过敏原/忌口"), m_allergens);

    auto *buttons = new QDialogButtonBox(QDialogButtonBox::Ok | QDialogButtonBox::Cancel, this);
    buttons->button(QDialogButtonBox::Ok)->setText(QStringLiteral("保存"));
    buttons->button(QDialogButtonBox::Ok)->setObjectName(QStringLiteral("PrimaryBtn"));
    buttons->button(QDialogButtonBox::Cancel)->setText(QStringLiteral("取消"));
    buttons->button(QDialogButtonBox::Cancel)->setObjectName(QStringLiteral("GhostBtn"));

    auto *lay = new QVBoxLayout(this);
    lay->setContentsMargins(24, 24, 24, 18);
    lay->setSpacing(16);
    auto *tip = new QLabel(QStringLiteral("档案信息将用于热量目标计算与个性化饮食建议，保存后同步到服务器数据库"), this);
    tip->setObjectName(QStringLiteral("HintText"));
    tip->setWordWrap(true);
    lay->addWidget(tip);
    lay->addLayout(form);
    lay->addWidget(buttons);

    // 回填当前值
    ProfileService &pf = ProfileService::instance();
    m_nickname->setText(pf.nickname());
    m_gender->setCurrentText(pf.gender());
    m_age->setValue(pf.age());
    m_height->setValue(pf.heightCm());
    m_weight->setValue(pf.weightKg());
    m_activity->setCurrentText(pf.activityLevel());
    m_targetCal->setValue(pf.targetCalorie());
    m_allergens->setText(pf.allergens());
    m_originalWeight = pf.weightKg();

    connect(estimateBtn, &QPushButton::clicked, this, &ProfileDialog::estimateTargetCalorie);
    connect(buttons, &QDialogButtonBox::accepted, this, &QDialog::accept);
    connect(buttons, &QDialogButtonBox::rejected, this, &QDialog::reject);
}

void ProfileDialog::estimateTargetCalorie()
{
    ProfileService &pf = ProfileService::instance();
    pf.setGender(m_gender->currentText());
    pf.setAge(m_age->value());
    pf.setHeightCm(m_height->value());
    pf.setWeightKg(m_weight->value());
    pf.setActivityLevel(m_activity->currentText());
    m_targetCal->setValue(pf.suggestTargetCalorie());
}

bool ProfileDialog::apply()
{
    ProfileService &pf = ProfileService::instance();
    pf.setNickname(m_nickname->text());
    pf.setGender(m_gender->currentText());
    pf.setAge(m_age->value());
    pf.setHeightCm(m_height->value());
    // 体重变化时自动追加一条今日体重记录
    const double newWeight = m_weight->value();
    if (qAbs(newWeight - m_originalWeight) > 0.05)
        pf.setWeightKg(newWeight, QDate::currentDate());
    else
        pf.setWeightKg(newWeight);
    pf.setActivityLevel(m_activity->currentText());
    pf.setTargetCalorie(m_targetCal->value());
    pf.setAllergens(m_allergens->text());

    // 保存到后端（档案 + 今日体重），失败仅提示不阻断界面
    pf.saveToBackend([](bool ok, const QString &err) {
        if (!ok)
            QMessageBox::warning(nullptr, QStringLiteral("提示"),
                                 QStringLiteral("已保存到本地，但同步服务器失败：%1").arg(err));
    });
    return true;
}
