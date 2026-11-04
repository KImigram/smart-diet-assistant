#pragma once
// ============================================================
// 环形图组件（QPainter 自绘）：占比展示 + 图例
// ============================================================
#include <QColor>
#include <QString>
#include <QStringList>
#include <QVector>
#include <QWidget>

class DonutChart : public QWidget
{
    Q_OBJECT
public:
    explicit DonutChart(QWidget *parent = nullptr);

    void setTitle(const QString &title);
    void setData(const QStringList &labels, const QVector<double> &values,
                 const QVector<QColor> &colors,
                 const QString &centerTitle, const QString &centerValue);

protected:
    void paintEvent(QPaintEvent *event) override;

private:
    QString     m_title;
    QStringList m_labels;
    QVector<double> m_values;
    QVector<QColor> m_colors;
    QString     m_centerTitle;
    QString     m_centerValue;
};
