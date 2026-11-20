#include "RecognitionPage.h"

#include <QButtonGroup>
#include <QComboBox>
#include <QDoubleSpinBox>
#include <QGridLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QMessageBox>
#include <QProgressBar>
#include <QPushButton>
#include <QRadioButton>
#include <QScrollArea>
#include <QTimer>
#include <QVBoxLayout>

#include "../config.h"
#include "../models/MealRecord.h"
#include "../services/ApiClient.h"
#include "../services/NutritionService.h"
#include "../services/ProfileService.h"
#include "../services/RecognitionService.h"
#include "../services/RecordService.h"
#include "../widgets/DropImageArea.h"
#include "../widgets/FoodPickerDialog.h"
#include "../widgets/MetricCard.h"

RecognitionPage::RecognitionPage(QWidget *parent)
    : QWidget(parent)
{
    // 整体放入滚动区：窗口高度不足时出现滚动条，而不是压缩卡片内容
    auto *root = new QVBoxLayout(this);
    root->setContentsMargins(0, 0, 0, 0);
    root->setSpacing(0);

    auto *scroll = new QScrollArea(this);
    scroll->setObjectName(QStringLiteral("pageScroll"));
    scroll->setWidgetResizable(true);
    scroll->setFrameShape(QFrame::NoFrame);
    scroll->setStyleSheet(QStringLiteral(
        "QScrollArea#pageScroll { background: transparent; border: none; }"
        "QScrollArea#pageScroll > QWidget > QWidget#scrollContent { background: transparent; }"));

    auto *content = new QWidget(scroll);
    content->setObjectName(QStringLiteral("scrollContent"));
    // 最小内容高度：低于此高度时滚动而非压缩，保证营养计算卡片文字完整可见
    content->setMinimumHeight(820);

    auto *lay = new QVBoxLayout(content);
    lay->setContentsMargins(24, 20, 24, 16);
    lay->setSpacing(14);

    auto *title = new QLabel(QStringLiteral("菜品识别"), content);
    title->setObjectName(QStringLiteral("PageTitle"));
    auto *subtitle = new QLabel(
        QStringLiteral("上传菜品照片，本地微调模型自动识别菜名并计算营养摄入"), content);
    subtitle->setObjectName(QStringLiteral("PageSubtitle"));
    subtitle->setWordWrap(true);
    lay->addWidget(title);
    lay->addWidget(subtitle);

    auto *body = new QHBoxLayout;
    body->setSpacing(16);
    body->addWidget(buildLeftPanel(), 5);
    body->addWidget(buildRightPanel(), 6);
    lay->addLayout(body, 1);

    scroll->setWidget(content);
    root->addWidget(scroll, 1);

    // 连接识别服务信号
    RecognitionService &rs = RecognitionService::instance();
    connect(&rs, &RecognitionService::recognized, this, &RecognitionPage::onRecognized);
    connect(&rs, &RecognitionService::error, this, &RecognitionPage::onRecognizeError);

    // 连接记录服务信号
    RecordService &recs = RecordService::instance();
    connect(&recs, &RecordService::recordAdded, this, &RecognitionPage::onRecordAdded);
}

QWidget *RecognitionPage::buildLeftPanel()
{
    auto *card = new QFrame(this);
    card->setObjectName(QStringLiteral("Card"));
    auto *lay = new QVBoxLayout(card);
    lay->setContentsMargins(16, 16, 16, 16);
    lay->setSpacing(12);

    auto *cardTitle = new QLabel(QStringLiteral("上传图片"), card);
    cardTitle->setObjectName(QStringLiteral("CardTitle"));
    lay->addWidget(cardTitle);

    m_dropArea = new DropImageArea(card);
    lay->addWidget(m_dropArea, 1);

    auto *btnRow = new QHBoxLayout;
    btnRow->setSpacing(10);

    auto *btnSelect = new QPushButton(QStringLiteral("选择图片"), card);
    btnSelect->setObjectName(QStringLiteral("SecondaryBtn"));

    m_btnRecognize = new QPushButton(QStringLiteral("开始识别"), card);
    m_btnRecognize->setObjectName(QStringLiteral("btnRecognize"));
    m_btnRecognize->setEnabled(false);

    btnRow->addWidget(btnSelect);
    btnRow->addStretch(1);
    btnRow->addWidget(m_btnRecognize);
    lay->addLayout(btnRow);

    connect(btnSelect, &QPushButton::clicked, this, [this]() {
        m_dropArea->chooseImage();
    });
    connect(m_btnRecognize, &QPushButton::clicked, this, &RecognitionPage::onRecognizeClicked);
    connect(m_dropArea, &DropImageArea::imageSelected, this, [this](const QString &path) {
        m_lastImagePath = path;
        m_btnRecognize->setEnabled(true);
        showToast(QStringLiteral("图片已选择，点击「开始识别」"));
    });

    return card;
}

QWidget *RecognitionPage::buildRightPanel()
{
    auto *right = new QWidget(this);
    auto *lay = new QVBoxLayout(right);
    lay->setContentsMargins(0, 0, 0, 0);
    lay->setSpacing(14);

    // 识别结果
    auto *candCard = new QFrame(right);
    candCard->setObjectName(QStringLiteral("Card"));
    auto *candLay = new QVBoxLayout(candCard);
    candLay->setContentsMargins(16, 14, 16, 14);
    candLay->setSpacing(10);

    auto *candTitle = new QLabel(QStringLiteral("识别结果"), candCard);
    candTitle->setObjectName(QStringLiteral("CardTitle"));
    candLay->addWidget(candTitle);

    m_candidateLayout = new QVBoxLayout;
    m_candidateLayout->setSpacing(8);
    m_candidateHint = new QLabel(QStringLiteral("尚未识别。请上传图片后点击「开始识别」。"), candCard);
    m_candidateHint->setObjectName(QStringLiteral("HintText"));
    m_candidateHint->setWordWrap(true);
    m_candidateLayout->addWidget(m_candidateHint);
    candLay->addLayout(m_candidateLayout);
    lay->addWidget(candCard);

    // 记录信息
    auto *recCard = new QFrame(right);
    recCard->setObjectName(QStringLiteral("Card"));
    auto *recLay = new QVBoxLayout(recCard);
    recLay->setContentsMargins(16, 14, 16, 14);
    recLay->setSpacing(10);

    auto *recTitle = new QLabel(QStringLiteral("记录信息"), recCard);
    recTitle->setObjectName(QStringLiteral("CardTitle"));
    recLay->addWidget(recTitle);

    auto *formRow = new QHBoxLayout;
    formRow->setSpacing(10);
    auto *mealLabel = new QLabel(QStringLiteral("餐次"), recCard);
    m_mealCombo = new QComboBox(recCard);
    m_mealCombo->addItems(AppConfig::kMealTypes);

    auto *portionLabel = new QLabel(QStringLiteral("份量"), recCard);
    m_portionSpin = new QDoubleSpinBox(recCard);
    m_portionSpin->setRange(10.0, 3000.0);
    m_portionSpin->setSingleStep(10.0);
    m_portionSpin->setSuffix(QStringLiteral(" 克"));
    m_portionSpin->setValue(150.0);

    m_btnOnePortion = new QPushButton(QStringLiteral("1 份"), recCard);
    m_btnOnePortion->setObjectName(QStringLiteral("GhostBtn"));
    m_btnOnePortion->setEnabled(false);

    formRow->addWidget(mealLabel);
    formRow->addWidget(m_mealCombo);
    formRow->addSpacing(8);
    formRow->addWidget(portionLabel);
    formRow->addWidget(m_portionSpin, 1);
    formRow->addWidget(m_btnOnePortion);
    recLay->addLayout(formRow);
    lay->addWidget(recCard);

    // 营养计算
    auto *nutCard = new QFrame(right);
    nutCard->setObjectName(QStringLiteral("Card"));
    auto *nutLay = new QVBoxLayout(nutCard);
    nutLay->setContentsMargins(16, 14, 16, 14);
    nutLay->setSpacing(10);

    auto *nutRow = new QHBoxLayout;
    auto *nutTitle = new QLabel(QStringLiteral("营养计算"), nutCard);
    nutTitle->setObjectName(QStringLiteral("CardTitle"));
    m_targetLabel = new QLabel(nutCard);
    m_targetLabel->setObjectName(QStringLiteral("HintText"));
    m_targetLabel->setText(QStringLiteral("每日目标 %1 kcal")
                               .arg(qRound(ProfileService::instance().targetCalorie())));
    nutRow->addWidget(nutTitle);
    nutRow->addStretch(1);
    nutRow->addWidget(m_targetLabel);
    nutLay->addLayout(nutRow);

    auto *grid = new QGridLayout;
    grid->setSpacing(10);
    m_cardCal = new MetricCard(nutCard);
    m_cardProtein = new MetricCard(nutCard);
    m_cardFat = new MetricCard(nutCard);
    m_cardCarb = new MetricCard(nutCard);
    m_cardFiber = new MetricCard(nutCard);
    m_cardSodium = new MetricCard(nutCard);
    grid->addWidget(m_cardCal, 0, 0);
    grid->addWidget(m_cardProtein, 0, 1);
    grid->addWidget(m_cardFat, 0, 2);
    grid->addWidget(m_cardCarb, 1, 0);
    grid->addWidget(m_cardFiber, 1, 1);
    grid->addWidget(m_cardSodium, 1, 2);
    nutLay->addLayout(grid);
    lay->addWidget(nutCard, 1);

    // 操作按钮
    auto *btnRow = new QHBoxLayout;
    m_btnConfirm = new QPushButton(QStringLiteral("确认记录到饮食记录"), right);
    m_btnConfirm->setObjectName(QStringLiteral("PrimaryBtn"));
    m_btnConfirm->setEnabled(false);
    auto *btnCorrect = new QPushButton(QStringLiteral("识别有误？纠错"), right);
    btnCorrect->setObjectName(QStringLiteral("LinkBtn"));
    m_toast = new QLabel(right);
    m_toast->setObjectName(QStringLiteral("ToastLabel"));
    m_toast->setWordWrap(true);

    btnRow->addWidget(m_btnConfirm);
    btnRow->addWidget(btnCorrect);
    btnRow->addSpacing(8);
    btnRow->addWidget(m_toast, 1);
    lay->addLayout(btnRow);

    connect(m_btnConfirm, &QPushButton::clicked, this, &RecognitionPage::onConfirmRecord);
    connect(btnCorrect, &QPushButton::clicked, this, &RecognitionPage::onCorrectClicked);
    connect(m_portionSpin, QOverload<double>::of(&QDoubleSpinBox::valueChanged),
            this, &RecognitionPage::onUpdatePortionStep);
    connect(m_btnOnePortion, &QPushButton::clicked, this, &RecognitionPage::onOnePortionClicked);

    resetNutritionCards();
    return right;
}

void RecognitionPage::clearCandidates()
{
    // 清空布局中所有候选行容器（最关键：之前只删了radio/bar/pct，没删line容器）
    while (m_candidateLayout->count()) {
        QLayoutItem *item = m_candidateLayout->takeAt(0);
        if (item->widget())
            item->widget()->deleteLater();
        delete item;
    }
    for (const CandidateRow &row : m_candidates) {
        if (row.radio) row.radio->deleteLater();
        if (row.bar) row.bar->deleteLater();
        if (row.pct) row.pct->deleteLater();
    }
    m_candidates.clear();
    m_estimating = false;
    m_selectedName.clear();
    m_selectedFoodId = 0;
    m_selectedCal100g = 0.0;
    m_selectedPro100g = 0.0;
    m_selectedFat100g = 0.0;
    m_selectedCarb100g = 0.0;
    m_selectedFiber100g = 0.0;
    m_selectedSodium100g = 0.0;
    m_btnConfirm->setEnabled(false);
    m_btnOnePortion->setEnabled(false);
    m_candidateHint = nullptr;
}

void RecognitionPage::onRecognizeClicked()
{
    if (!m_dropArea->hasImage() || m_isRecognizing)
        return;

    m_isRecognizing = true;
    m_btnRecognize->setEnabled(false);
    m_btnRecognize->setText(QStringLiteral("识别中…"));
    clearCandidates();

    m_candidateHint = new QLabel(QStringLiteral("正在加载…"), this);
    m_candidateHint->setObjectName(QStringLiteral("HintText"));
    m_candidateLayout->addWidget(m_candidateHint);

    RecognitionService::instance().recognize(m_lastImagePath);
}

void RecognitionPage::onRecognized(const QVector<RecognitionCandidate> &candidates, bool needConfirm)
{
    m_isRecognizing = false;
    m_btnRecognize->setEnabled(true);
    m_btnRecognize->setText(QStringLiteral("开始识别"));
    clearCandidates();

    if (candidates.isEmpty()) {
        m_candidateHint = new QLabel(QStringLiteral("未能识别出菜品，请尝试重新拍照或手动录入。"), this);
        m_candidateHint->setObjectName(QStringLiteral("HintText"));
        m_candidateHint->setWordWrap(true);
        m_candidateLayout->addWidget(m_candidateHint);
        resetNutritionCards();
        return;
    }

    auto *group = new QButtonGroup(this);
    for (const RecognitionCandidate &c : candidates) {
        CandidateRow row;
        row.name = c.name;
        row.foodId = c.foodId;
        row.confidence = c.confidence;
        row.caloriePer100g = c.caloriePer100g;
        row.proteinPer100g = c.proteinPer100g;

        auto *line = new QWidget(this);
        auto *v = new QVBoxLayout(line);
        v->setContentsMargins(4, 2, 4, 2);
        v->setSpacing(2);

        auto *h = new QHBoxLayout;
        h->setSpacing(10);

        QString label = c.name;
        if (c.fromCorrection)
            label += QStringLiteral("（纠错匹配）");
        if (c.foodId == 0)
            label += QStringLiteral("（未收录）");

        row.radio = new QRadioButton(label, line);
        row.radio->setStyleSheet(QStringLiteral("font-size: 14px; font-weight: 600;"));
        group->addButton(row.radio);

        row.bar = new QProgressBar(line);
        row.bar->setObjectName(QStringLiteral("ConfBar"));
        row.bar->setRange(0, 100);
        row.bar->setValue(qRound(c.confidence * 100.0));
        row.bar->setTextVisible(false);
        row.bar->setFixedWidth(120);
        row.bar->setFixedHeight(8);

        row.pct = new QLabel(QStringLiteral("%1%").arg(qRound(c.confidence * 100.0)), line);
        row.pct->setObjectName(QStringLiteral("HintText"));
        row.pct->setFixedWidth(44);

        h->addWidget(row.radio);
        h->addWidget(row.bar);
        h->addStretch(1);
        h->addWidget(row.pct);
        v->addLayout(h);

        // 主要食材（基座模型补充，避免漏掉米饭等主食信息）
        if (!c.ingredients.trimmed().isEmpty()) {
            auto *ing = new QLabel(QStringLiteral("主要食材：%1").arg(c.ingredients), line);
            ing->setObjectName(QStringLiteral("HintText"));
            ing->setWordWrap(true);
            ing->setStyleSheet(QStringLiteral("color:#8b949e; font-size:12px;"));
            v->addWidget(ing);
        }

        m_candidateLayout->addWidget(line);

        connect(row.radio, &QRadioButton::toggled, this, [this, row](bool checked) {
            if (checked) {
                m_selectedName = row.name;
                m_selectedFoodId = row.foodId;
                m_selectedCal100g = row.caloriePer100g;
                m_selectedPro100g = row.proteinPer100g;
                m_selectedFat100g = 0.0;
                m_selectedCarb100g = 0.0;
                m_selectedFiber100g = 0.0;
                m_selectedSodium100g = 0.0;
                m_btnConfirm->setEnabled(row.foodId > 0);
                m_btnOnePortion->setEnabled(true);
                // 未收录候选 → 自动调 AI 估算营养并入库（无需手动操作）
                if (row.foodId <= 0 && !m_estimating)
                    onEstimateClicked();
                updateNutritionPreview();
            }
        });

        m_candidates << row;
    }

    if (!m_candidates.isEmpty())
        m_candidates.first().radio->setChecked(true);

    if (needConfirm)
        showToast(QStringLiteral("识别置信度较低，请确认正确的菜品"));
    else
        showToast(QStringLiteral("识别完成"));
}

void RecognitionPage::onRecognizeError(const QString &msg)
{
    m_isRecognizing = false;
    m_btnRecognize->setEnabled(true);
    m_btnRecognize->setText(QStringLiteral("开始识别"));
    clearCandidates();
    m_candidateHint = new QLabel(msg, this);
    m_candidateHint->setObjectName(QStringLiteral("HintText"));
    m_candidateHint->setWordWrap(true);
    m_candidateHint->setStyleSheet(QStringLiteral("color:#E5484D;"));
    m_candidateLayout->addWidget(m_candidateHint);
}

void RecognitionPage::onUpdatePortionStep()
{
    if (!m_selectedName.isEmpty())
        updateNutritionPreview();
}

void RecognitionPage::updateNutritionPreview()
{
    if (m_selectedName.isEmpty() || m_selectedFoodId == 0) {
        resetNutritionCards();
        return;
    }
    // 用选中候选的每100g数据 * 份量（选中时已存入成员变量，不再反查）
    const double portion = m_portionSpin->value();
    const double factor = portion / 100.0;
    const double cal100 = m_selectedCal100g;
    const double pro100 = m_selectedPro100g;
    const double fat100 = m_selectedFat100g;
    const double carb100 = m_selectedCarb100g;
    const double fiber100 = m_selectedFiber100g;
    const double sodium100 = m_selectedSodium100g;

    const QColor green(0x2E, 0x9E, 0x6B), blue(0x3B, 0x82, 0xF6),
                 orange(0xF5, 0xA6, 0x23), purple(0x8E, 0x6F, 0xD8);
    const double targetCal = ProfileService::instance().targetCalorie();

    m_cardCal->setMetric(QStringLiteral("热量"), QString::number(qRound(cal100 * factor)),
                         QStringLiteral("/ %1 kcal").arg(qRound(targetCal)),
                         targetCal > 0 ? cal100 * factor / targetCal : -1.0, green);
    m_cardProtein->setMetric(QStringLiteral("蛋白质"), QString::number(pro100 * factor, 'f', 1),
                             QStringLiteral("g"), -1, blue);
    m_cardFat->setMetric(QStringLiteral("脂肪"), QString::number(fat100 * factor, 'f', 1),
                         QStringLiteral("g"), -1, orange);
    m_cardCarb->setMetric(QStringLiteral("碳水"), QString::number(carb100 * factor, 'f', 1),
                          QStringLiteral("g"), -1, purple);
    m_cardFiber->setMetric(QStringLiteral("膳食纤维"), QString::number(fiber100 * factor, 'f', 1),
                           QStringLiteral("g"), -1, green);
    m_cardSodium->setMetric(QStringLiteral("钠"), QString::number(qRound(sodium100 * factor)),
                            QStringLiteral("mg"), -1, orange);
}

void RecognitionPage::onOnePortionClicked()
{
    // 默认一份设为150g（后端有default_portion_g但候选里没带，用默认值）
    m_portionSpin->setValue(150.0);
}

void RecognitionPage::onConfirmRecord()
{
    if (m_selectedFoodId <= 0) {
        QMessageBox::information(this, QStringLiteral("提示"),
                                 QStringLiteral("该菜品未收录到食物库，请选择其他候选或纠错"));
        return;
    }
    m_btnConfirm->setEnabled(false);
    RecordService::instance().addRecord(
        m_selectedFoodId, m_mealCombo->currentText(),
        m_portionSpin->value(), QDateTime::currentDateTime());
}

void RecognitionPage::onRecordAdded(const MealRecord &record)
{
    m_btnConfirm->setEnabled(true);
    showToast(QStringLiteral("✓ 已记录：%1 · %2 · %3 克")
                  .arg(record.foodName, record.mealType)
                  .arg(qRound(record.portionG)));
}

void RecognitionPage::onCorrectClicked()
{
    if (m_selectedName.isEmpty()) {
        QMessageBox::information(this, QStringLiteral("提示"), QStringLiteral("请先完成一次识别后再纠错"));
        return;
    }

    // 保存原始识别名（用于纠错API），之后 m_selectedName 会被替换为纠正后的食物名
    const QString recognizedName = m_selectedName;

    FoodPickerDialog dlg(this);
    dlg.setWindowTitle(QStringLiteral("识别纠错"));
    dlg.setOriginalName(recognizedName);

    if (dlg.exec() != QDialog::Accepted)
        return;
    const QString corrected = dlg.selectedFood();
    if (corrected.isEmpty())
        return;

    // 找到纠正后食物的ID和营养数据
    const FoodItem *f = NutritionService::instance().findByName(corrected);
    if (!f) {
        QMessageBox::warning(this, QStringLiteral("提示"), QStringLiteral("选择的食物不在库中"));
        return;
    }

    // 立即将当前选中替换为纠正后的食物 → 营养预览刷新 + 确认按钮可用
    m_selectedName = corrected;
    m_selectedFoodId = f->id;
    m_selectedCal100g = f->per100g.cal;
    m_selectedPro100g = f->per100g.protein;
    m_btnConfirm->setEnabled(true);
    m_btnOnePortion->setEnabled(true);
    updateNutritionPreview();

    // 调用纠错API记住映射，后续识别自动优先匹配
    QJsonObject body;
    body["user_id"] = g_currentUserId;
    body["recognized_name"] = recognizedName;
    body["correct_food_id"] = f->id;
    ApiClient::instance().postJson(
        QStringLiteral("/api/recognize/correct"), body,
        [this, corrected](const QJsonDocument &) {
            showToast(QStringLiteral("已纠正为「%1」，可直接确认记录").arg(corrected));
        },
        [this](const QString &err) {
            showToast(QStringLiteral("已纠正，但映射保存失败: %1").arg(err));
        });
}

void RecognitionPage::onEstimateClicked()
{
    if (m_selectedName.isEmpty() || m_estimating)
        return;
    if (m_selectedFoodId > 0) {
        showToast(QStringLiteral("该菜品已收录，无需估算"));
        return;
    }

    m_estimating = true;
    showToast(QStringLiteral("正在调用 AI 估算「%1」的营养并入库…").arg(m_selectedName));

    QJsonObject body;
    body["name"] = m_selectedName;
    body["user_id"] = g_currentUserId;
    ApiClient::instance().postJson(
        QStringLiteral("/api/recognize/estimate"), body,
        [this](const QJsonDocument &doc) {
            m_estimating = false;
            const QJsonObject obj = doc.object();
            const int foodId = obj.value("food_id").toInt();
            if (foodId <= 0) {
                showToast(QStringLiteral("AI 估算失败，请重试或纠错"));
                return;
            }
            const QJsonObject nut = obj.value("nutrition").toObject();
            m_selectedFoodId = foodId;
            m_selectedCal100g = nut.value("calorie").toDouble();
            m_selectedPro100g = nut.value("protein").toDouble();
            m_selectedFat100g = nut.value("fat").toDouble();
            m_selectedCarb100g = nut.value("carb").toDouble();
            m_selectedFiber100g = nut.value("fiber").toDouble();
            m_selectedSodium100g = nut.value("sodium").toDouble();
            m_btnConfirm->setEnabled(true);
            updateNutritionPreview();
            showToast(QStringLiteral("✓ AI 已估算「%1」营养并加入食物库，可直接确认记录").arg(m_selectedName));
        },
        [this](const QString &err) {
            m_estimating = false;
            showToast(QStringLiteral("估算失败: %1").arg(err));
        });
}

void RecognitionPage::resetNutritionCards()
{
    const QColor green(0x2E, 0x9E, 0x6B), blue(0x3B, 0x82, 0xF6),
                 orange(0xF5, 0xA6, 0x23), purple(0x8E, 0x6F, 0xD8);
    m_cardCal->setMetric(QStringLiteral("热量"), QStringLiteral("--"), QStringLiteral("kcal"), -1, green);
    m_cardProtein->setMetric(QStringLiteral("蛋白质"), QStringLiteral("--"), QStringLiteral("g"), -1, blue);
    m_cardFat->setMetric(QStringLiteral("脂肪"), QStringLiteral("--"), QStringLiteral("g"), -1, orange);
    m_cardCarb->setMetric(QStringLiteral("碳水"), QStringLiteral("--"), QStringLiteral("g"), -1, purple);
    m_cardFiber->setMetric(QStringLiteral("膳食纤维"), QStringLiteral("--"), QStringLiteral("g"), -1, green);
    m_cardSodium->setMetric(QStringLiteral("钠"), QStringLiteral("--"), QStringLiteral("mg"), -1, orange);
}

void RecognitionPage::showToast(const QString &text)
{
    if (m_toast) {
        m_toast->setText(text);
        QTimer::singleShot(4000, this, [this]() {
            if (m_toast) m_toast->clear();
        });
    }
}
