#pragma once
// ============================================================
// 柱状图组件（QPainter 自绘）：支持目标参考线、数值标签
// ============================================================
#include <QColor>
#include <QString>
#include <QStringList>
#include <QVector>
#include <QWidget>

class BarChart : public QWidget
{
    Q_OBJECT
public:
    explicit BarChart(QWidget *parent = nullptr);

    void setTitle(const QString &title);
    void setData(const QStringList &labels, const QVector<double> &values,
                 double target, const QString &unit);
    void setBarColor(const QColor &color);

protected:
    void paintEvent(QPaintEvent *event) override;

private:
    QString     m_title;
    QStringList m_labels;
    QVector<double> m_values;
    double      m_target = -1.0;
    QString     m_unit;
    QColor      m_barColor = QColor(0x2E, 0x9E, 0x6B);
};
