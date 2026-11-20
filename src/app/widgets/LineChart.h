#pragma once
// ============================================================
// 简单折线图控件（QPainter 绘制，用于体重趋势等）
// ============================================================
#include <QColor>
#include <QString>
#include <QStringList>
#include <QVector>
#include <QWidget>

class LineChart : public QWidget
{
    Q_OBJECT
public:
    explicit LineChart(QWidget *parent = nullptr);

    void setData(const QStringList &labels, const QVector<double> &values,
                 const QColor &lineColor = QColor(0x2E, 0x9E, 0x6B));
    void setUnit(const QString &unit) { m_unit = unit; }

    QSize minimumSizeHint() const override { return QSize(200, 140); }
    QSize sizeHint() const override { return QSize(400, 180); }

protected:
    void paintEvent(QPaintEvent *event) override;

private:
    QStringList    m_labels;
    QVector<double> m_values;
    QColor         m_lineColor;
    QString        m_unit;
};
