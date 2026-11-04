#pragma once
// ============================================================
// 界面 1 · 菜品识别页（接入后端API）
// 流程：上传图片 → 本地微调模型识别 → 选择菜名 → 营养预览 → 确认记录
// ============================================================
#include <QVector>
#include <QWidget>

#include "../models/RecognitionCandidate.h"

class QComboBox;
class QDoubleSpinBox;
class QLabel;
class QProgressBar;
class QPushButton;
class QRadioButton;
class QVBoxLayout;
class DropImageArea;
class MetricCard;

struct CandidateRow
{
    QString        name;
    int            foodId = 0;
    double         confidence = 0.0;
    double         caloriePer100g = 0.0;
    double         proteinPer100g = 0.0;
    QRadioButton  *radio = nullptr;
    QProgressBar  *bar = nullptr;
    QLabel        *pct = nullptr;
};

class RecognitionPage : public QWidget
{
    Q_OBJECT
public:
    explicit RecognitionPage(QWidget *parent = nullptr);

private slots:
    void onRecognizeClicked();
    void onRecognized(const QVector<RecognitionCandidate> &candidates, bool needConfirm);
    void onRecognizeError(const QString &msg);
    void onOnePortionClicked();
    void onConfirmRecord();
    void onRecordAdded(const struct MealRecord &record);
    void onCorrectClicked();
    void onUpdatePortionStep();
    void onEstimateClicked();

private:
    QWidget *buildLeftPanel();
    QWidget *buildRightPanel();
    void updateNutritionPreview();
    void showToast(const QString &text);
    void resetNutritionCards();
    void clearCandidates();

    DropImageArea   *m_dropArea = nullptr;
    QPushButton     *m_btnRecognize = nullptr;
    QPushButton     *m_btnConfirm = nullptr;
    QComboBox       *m_mealCombo = nullptr;
    QDoubleSpinBox  *m_portionSpin = nullptr;
    QPushButton     *m_btnOnePortion = nullptr;
    QVBoxLayout     *m_candidateLayout = nullptr;
    QLabel          *m_candidateHint = nullptr;
    QLabel          *m_toast = nullptr;
    QLabel          *m_targetLabel = nullptr;

    MetricCard *m_cardCal = nullptr, *m_cardProtein = nullptr, *m_cardFat = nullptr;
    MetricCard *m_cardCarb = nullptr, *m_cardFiber = nullptr, *m_cardSodium = nullptr;

    QVector<CandidateRow> m_candidates;
    int m_selectedFoodId = 0;
    QString m_selectedName;
    double m_selectedCal100g = 0.0;
    double m_selectedPro100g = 0.0;
    double m_selectedFat100g = 0.0;
    double m_selectedCarb100g = 0.0;
    double m_selectedFiber100g = 0.0;
    double m_selectedSodium100g = 0.0;
    QString m_lastImagePath;
    bool m_isRecognizing = false;
    bool m_estimating = false;
};
