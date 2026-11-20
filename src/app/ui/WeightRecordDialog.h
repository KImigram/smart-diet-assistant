#pragma once
// ============================================================
// 体重录入对话框（轻量：体重 + 日期）
// ============================================================
#include <QDialog>

class QDateEdit;
class QDoubleSpinBox;

class WeightRecordDialog : public QDialog
{
    Q_OBJECT
public:
    explicit WeightRecordDialog(QWidget *parent = nullptr);

    double weightKg() const;
    QDate  date() const;

private:
    QDoubleSpinBox *m_weight = nullptr;
    QDateEdit      *m_date = nullptr;
};
