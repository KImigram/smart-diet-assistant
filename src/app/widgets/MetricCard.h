#pragma once
// ============================================================
// 指标卡：标题 + 数值/单位 + 达标进度条
// ============================================================
#include <QColor>
#include <QFrame>
#include <QString>

class QLabel;
class QProgressBar;

class MetricCard : public QFrame
{
    Q_OBJECT
public:
    explicit MetricCard(QWidget *parent = nullptr);

    // progress 传入 0~1 表示进度条填充比例；传入 <0 隐藏进度条
    void setMetric(const QString &title, const QString &value, const QString &unit,
                   double progress, const QColor &color);

    void setCaption(const QString &text);

private:
    QLabel       *m_title = nullptr;
    QLabel       *m_value = nullptr;
    QLabel       *m_caption = nullptr;
    QProgressBar *m_bar = nullptr;
};
