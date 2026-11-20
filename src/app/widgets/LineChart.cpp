#include "LineChart.h"

#include <QFontMetrics>
#include <QPainter>
#include <QPainterPath>
#include <QPen>

LineChart::LineChart(QWidget *parent)
    : QWidget(parent)
    , m_lineColor(0x2E, 0x9E, 0x6B)
{
    setMinimumHeight(140);
}

void LineChart::setData(const QStringList &labels, const QVector<double> &values,
                        const QColor &lineColor)
{
    m_labels = labels;
    m_values = values;
    m_lineColor = lineColor;
    update();
}

void LineChart::paintEvent(QPaintEvent *event)
{
    Q_UNUSED(event)
    QPainter p(this);
    p.setRenderHint(QPainter::Antialiasing);

    const int leftPad = 44, rightPad = 16, topPad = 16, bottomPad = 28;
    const QRectF plot(leftPad, topPad, width() - leftPad - rightPad, height() - topPad - bottomPad);

    if (m_values.isEmpty() || m_values.size() < 2) {
        p.setPen(QColor(0x8A, 0x99, 0xA9));
        QFont f = font();
        f.setPointSize(9);
        p.setFont(f);
        p.drawText(rect(), Qt::AlignCenter, QStringLiteral("暂无数据"));
        return;
    }

    // Y 轴范围
    double minV = m_values.first(), maxV = m_values.first();
    for (double v : m_values) {
        minV = qMin(minV, v);
        maxV = qMax(maxV, v);
    }
    const double range = maxV - minV;
    const double pad = qMax(range * 0.15, 0.5);
    minV -= pad;
    maxV += pad;
    const double yScale = plot.height() / qMax(0.01, maxV - minV);

    auto yOf = [&](double v) { return plot.bottom() - (v - minV) * yScale; };

    // 网格线 + Y 轴标签
    QFont lf = font();
    lf.setPointSize(8);
    p.setFont(lf);
    const int gridLines = 3;
    for (int i = 0; i <= gridLines; ++i) {
        const double v = minV + (maxV - minV) * i / gridLines;
        const double y = yOf(v);
        p.setPen(QPen(QColor(0xE8, 0xED, 0xF2), 1));
        p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y));
        p.setPen(QColor(0x8A, 0x99, 0xA9));
        p.drawText(QRectF(0, y - 8, leftPad - 6, 16),
                   Qt::AlignRight | Qt::AlignVCenter,
                   QString::number(v, 'f', 1));
    }

    // 折线
    const int n = m_values.size();
    const double xStep = plot.width() / qMax(1, n - 1);
    QVector<QPointF> points;
    for (int i = 0; i < n; ++i) {
        points << QPointF(plot.left() + i * xStep, yOf(m_values.at(i)));
    }

    // 渐变填充区域
    QLinearGradient grad(0, plot.top(), 0, plot.bottom());
    grad.setColorAt(0, QColor(m_lineColor.red(), m_lineColor.green(), m_lineColor.blue(), 40));
    grad.setColorAt(1, QColor(m_lineColor.red(), m_lineColor.green(), m_lineColor.blue(), 0));
    QPainterPath area;
    area.moveTo(points.first().x(), plot.bottom());
    for (const auto &pt : points)
        area.lineTo(pt);
    area.lineTo(points.last().x(), plot.bottom());
    area.closeSubpath();
    p.fillPath(area, grad);

    // 线条
    p.setPen(QPen(m_lineColor, 2.5));
    p.drawPolyline(points.constData(), points.size());

    // 数据点
    p.setPen(Qt::NoPen);
    p.setBrush(m_lineColor);
    for (const auto &pt : points)
        p.drawEllipse(pt, 3.5, 3.5);

    // 最新点高亮 + 数值标签
    if (!points.isEmpty()) {
        const QPointF &last = points.last();
        p.setBrush(Qt::white);
        p.setPen(QPen(m_lineColor, 2));
        p.drawEllipse(last, 5, 5);
        p.setPen(m_lineColor);
        QFont vf = font();
        vf.setPointSize(9);
        vf.setBold(true);
        p.setFont(vf);
        const QString valText = QString("%1%2").arg(m_values.last(), 0, 'f', 1).arg(m_unit);
        const QFontMetrics fm(vf);
        const int tw = fm.horizontalAdvance(valText);
        double tx = last.x() - tw - 8;
        if (tx < plot.left())
            tx = last.x() + 10;
        p.drawText(QRectF(tx, last.y() - 18, tw + 4, 16),
                   Qt::AlignLeft | Qt::AlignVCenter, valText);
    }

    // X 轴标签（首尾 + 中间，避免重叠）
    p.setPen(QColor(0x8A, 0x99, 0xA9));
    p.setFont(lf);
    if (!m_labels.isEmpty()) {
        const int labelCount = qMin(5, n);
        for (int i = 0; i < labelCount; ++i) {
            const int idx = n <= 1 ? 0 : i * (n - 1) / (labelCount - 1);
            const double x = plot.left() + idx * xStep;
            p.drawText(QRectF(x - 30, plot.bottom() + 6, 60, 16),
                       Qt::AlignCenter, m_labels.value(idx));
        }
    }
}
