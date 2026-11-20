#pragma once
// ============================================================
// 食物选择对话框：搜索选择食物 + 可选记录字段（餐次/份量/时间）
// 用于「识别纠错」「手动添加记录」「编辑记录」三个场景
// ============================================================
#include <QDateTime>
#include <QDialog>
#include <QString>

class QLineEdit;
class QListWidget;
class QDoubleSpinBox;
class QComboBox;
class QDateTimeEdit;
class QPushButton;
struct MealRecord;

class FoodPickerDialog : public QDialog
{
    Q_OBJECT
public:
    explicit FoodPickerDialog(QWidget *parent = nullptr);

    // 纠错场景：预填原始识别名
    void setOriginalName(const QString &name);

    // 记录场景：启用餐次/份量/时间字段；prefill 用于编辑
    void setRecordFields(bool enable, const MealRecord *prefill = nullptr);

    // ---- 结果 ----
    QString selectedFood() const;
    double portionG() const;
    QString mealType() const;
    QDateTime eatenAt() const;

private slots:
    void onSearchChanged();
    void onListDoubleClicked();
    void updateOkState();

private:
    void refreshList();

    QLineEdit       *m_search = nullptr;
    QListWidget     *m_list = nullptr;
    QDoubleSpinBox  *m_portion = nullptr;
    QComboBox       *m_meal = nullptr;
    QDateTimeEdit   *m_time = nullptr;
    QPushButton     *m_ok = nullptr;
    bool             m_recordFields = false;
};
