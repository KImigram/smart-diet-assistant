#pragma once
// ============================================================
// 健康档案编辑对话框（对应 users / health_profile 表）
// ============================================================
#include <QDialog>

class QLineEdit;
class QComboBox;
class QSpinBox;
class QDoubleSpinBox;

class ProfileDialog : public QDialog
{
    Q_OBJECT
public:
    explicit ProfileDialog(QWidget *parent = nullptr);

    // 保存到 ProfileService；返回是否发生修改
    bool apply();

private slots:
    void estimateTargetCalorie();

private:
    QLineEdit      *m_nickname = nullptr;
    QComboBox      *m_gender = nullptr;
    QSpinBox       *m_age = nullptr;
    QDoubleSpinBox *m_height = nullptr;
    QDoubleSpinBox *m_weight = nullptr;
    QComboBox      *m_activity = nullptr;
    QDoubleSpinBox *m_targetCal = nullptr;
    QLineEdit      *m_allergens = nullptr;
    double          m_originalWeight = 0.0;  // 打开对话框时的体重，用于检测变化
};
