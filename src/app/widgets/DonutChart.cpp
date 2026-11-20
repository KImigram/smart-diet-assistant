#include "DonutChart.h"

#include <QPainter>

DonutChart::DonutChart(QWidget *parent)
    : QWidget(parent)
{
    setMinimumHeight(220);
}

void DonutChart::setTitle(const QString &title)
{
    m_title = title;
    update();
}

void DonutChart::setData(const QStringList &labels, const QVector<double> &values,
                         const QVector<QColor> &colors,
                         const QString &centerTitle, const QString &centerValue)
{
    m_labels = labels;
    m_values = values;
    m_colors = colors;
    m_centerTitle = centerTitle;
    m_centerValue = centerValue;
    update();
}

void DonutChart::paintEvent(QPaintEvent *event)
{
    Q_UNUSED(event)
    QPainter p(this);
    p.setRenderHint(QPainter::Antialiasing);

    const int titleH = 30;
    const int leftPad = 12, rightPad = 12;
    const int margin = 14;
    const qreal thickness = 24.0;

    // 标题
    p.setPen(QColor(0x22, 0x30, 0x3F));
    QFont tf = font();
    tf.setPointSize(11);
    tf.setBold(true);
    p.setFont(tf);
    p.drawText(QRect(leftPad, 4, width() - leftPad - rightPad, titleH),
               Qt::AlignLeft | Qt::AlignVCenter, m_title);

    double total = 0.0;
    for (double v : m_values)
        total += v;

    if (total <= 0.0 || m_values.isEmpty()) {
        p.setPen(QColor(0x8A, 0x99, 0xA9));
        QFont hf = font();
        hf.setPointSize(10);
        p.setFont(hf);
        p.drawText(rect().adjusted(0, titleH, 0, -10), Qt::AlignCenter,
                   QStringLiteral("暂无数据"));
        return;
    }

    // 环形图占左侧 56% 区域，图例占右侧；直径减去笔宽，确保外边缘不被裁剪
    const double donutAreaW = width() * 0.56;
    const double availH = height() - titleH - margin * 2;
    const double availW = donutAreaW - margin * 2;
    const double d = qMax(40.0, qMin(availH, availW) - thickness);
    const double donutX = margin + (donutAreaW - margin * 2 - d) / 2;
    const double donutY = titleH + margin + (availH - d) / 2;
    const QRectF donutRect(donutX, donutY, d, d);

    qreal startAngle = 90.0 * 16;   // 从正上方开始
    for (int i = 0; i < m_values.size(); ++i) {
        const qreal span = -360.0 * 16.0 * (m_values.at(i) / total);
        p.setPen(QPen(m_colors.at(i % m_colors.size()), thickness, Qt::SolidLine, Qt::RoundCap));
        p.drawArc(donutRect, static_cast<int>(startAngle), static_cast<int>(span));
        startAngle += span;
    }

    // 中心文字
    p.setPen(QColor(0x7A, 0x8B, 0x9C));
    QFont cf = font();
    cf.setPointSize(9);
    p.setFont(cf);
    p.drawText(donutRect.adjusted(0, -d * 0.12, 0, -d * 0.12), Qt::AlignCenter, m_centerTitle);
    p.setPen(QColor(0x22, 0x30, 0x3F));
    QFont cvf = font();
    cvf.setPointSize(15);
    cvf.setBold(true);
    p.setFont(cvf);
    p.drawText(donutRect.adjusted(0, d * 0.10, 0, d * 0.10), Qt::AlignCenter, m_centerValue);

    // 图例（右侧）
    const double legendX = donutAreaW + 4;
    const double legendW = width() - legendX - margin;
    const double rowH = 26.0;
    double y = donutRect.top() + 8;
    QFont lf = font();
    lf.setPointSize(10);
    p.setFont(lf);
    for (int i = 0; i < m_values.size(); ++i) {
        if (y + 18 > height() - 6)
            break;
        p.setPen(Qt::NoPen);
        p.setBrush(m_colors.at(i % m_colors.size()));
        p.drawRoundedRect(QRectF(legendX, y, 12, 12), 3, 3);
        p.setPen(QColor(0x22, 0x30, 0x3F));
        p.drawText(QRectF(legendX + 20, y - 3, legendW - 20, 18),
                   Qt::AlignLeft | Qt::AlignVCenter,
                   QStringLiteral("%1  %2%").arg(m_labels.at(i))
                       .arg(QString::number(m_values.at(i) / total * 100.0, 'f', 1)));
        y += rowH;
    }
}
