#include "BarChart.h"

#include <QFontMetrics>
#include <QPainter>
#include <QPen>

BarChart::BarChart(QWidget *parent)
    : QWidget(parent)
{
    setMinimumHeight(230);
}

void BarChart::setTitle(const QString &title)
{
    m_title = title;
    update();
}

void BarChart::setData(const QStringList &labels, const QVector<double> &values,
                       double target, const QString &unit)
{
    m_labels = labels;
    m_values = values;
    m_target = target;
    m_unit = unit;
    update();
}

void BarChart::setBarColor(const QColor &color)
{
    m_barColor = color;
    update();
}

void BarChart::paintEvent(QPaintEvent *event)
{
    Q_UNUSED(event)
    QPainter p(this);
    p.setRenderHint(QPainter::Antialiasing);

    const int titleH = 30;
    const int bottomH = 30;
    const int leftPad = 12, rightPad = 12;

    // 标题
    p.setPen(QColor(0x22, 0x30, 0x3F));
    QFont tf = font();
    tf.setPointSize(11);
    tf.setBold(true);
    p.setFont(tf);
    p.drawText(QRect(leftPad, 4, width() - leftPad - rightPad, titleH),
               Qt::AlignLeft | Qt::AlignVCenter, m_title);

    if (m_values.isEmpty()) {
        p.setPen(QColor(0x8A, 0x99, 0xA9));
        QFont hf = font();
        hf.setPointSize(10);
        p.setFont(hf);
        p.drawText(rect().adjusted(0, titleH, 0, -bottomH), Qt::AlignCenter,
                   QStringLiteral("暂无数据"));
        return;
    }

    // 画布
    const QRectF plot(leftPad, titleH + 6, width() - leftPad - rightPad, height() - titleH - bottomH - 10);
    const double baseY = plot.bottom();

    double maxV = 0.0;
    for (double v : m_values)
        maxV = qMax(maxV, v);
    if (m_target > 0)
        maxV = qMax(maxV, m_target);
    if (maxV <= 0)
        maxV = 1.0;
    maxV *= 1.2;  // 顶部留20%余量，避免数值标签与标题重合
    const double hScale = plot.height() / maxV;

    const int n = m_values.size();
    const double slotW = plot.width() / n;
    const double barW = slotW * 0.5;

    // 目标参考线
    if (m_target > 0) {
        const double ty = baseY - m_target * hScale;
        p.setPen(QPen(QColor(0xE5, 0x48, 0x4D), 1, Qt::DashLine));
        p.drawLine(QPointF(plot.left(), ty), QPointF(plot.right(), ty));
        // 目标标签放在线的右端，避免与标题重叠
        p.setPen(QColor(0xE5, 0x48, 0x4D));
        QFont lf = font();
        lf.setPointSize(8);
        p.setFont(lf);
        const QString targetText = QStringLiteral("目标 %1").arg(qRound(m_target));
        const QFontMetrics fm(lf);
        const int tw = fm.horizontalAdvance(targetText);
        p.drawText(QRectF(plot.right() - tw - 4, ty - 14, tw, 12),
                   Qt::AlignRight | Qt::AlignVCenter, targetText);
    }

    // 柱体 + 数值标签
    QFont vf = font();
    vf.setPointSize(8);
    for (int i = 0; i < n; ++i) {
        const double v = m_values.at(i);
        const double h = v * hScale;
        const QRectF bar(plot.left() + slotW * i + (slotW - barW) / 2,
                         baseY - h, barW, h);
        p.setPen(Qt::NoPen);
        p.setBrush(m_barColor);
        p.drawRoundedRect(bar, 4, 4);

        p.setPen(QColor(0x5A, 0x6B, 0x7C));
        p.setFont(vf);
        p.drawText(QRectF(bar.left() - 6, bar.top() - 16, bar.width() + 12, 14),
                   Qt::AlignCenter, QString::number(qRound(v)));
    }

    // X 轴标签
    QFont xf = font();
    xf.setPointSize(9);
    p.setFont(xf);
    p.setPen(QColor(0x7A, 0x8B, 0x9C));
    for (int i = 0; i < n; ++i) {
        const QRectF slot(plot.left() + slotW * i, plot.bottom() + 2, slotW, bottomH - 4);
        p.drawText(slot, Qt::AlignCenter, m_labels.at(i));
    }
}
