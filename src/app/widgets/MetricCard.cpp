#include "MetricCard.h"

#include <QLabel>
#include <QProgressBar>
#include <QVBoxLayout>

MetricCard::MetricCard(QWidget *parent)
    : QFrame(parent)
{
    setObjectName(QStringLiteral("Card"));
    setMinimumWidth(150);

    m_title = new QLabel(this);
    m_title->setObjectName(QStringLiteral("CardTitle"));

    m_value = new QLabel(this);
    m_value->setStyleSheet(QStringLiteral("font-size: 20px; font-weight: 700; color: #22303F;"));

    m_bar = new QProgressBar(this);
    m_bar->setObjectName(QStringLiteral("MetricBar"));
    m_bar->setRange(0, 100);
    m_bar->setTextVisible(false);
    m_bar->setFixedHeight(8);

    m_caption = new QLabel(this);
    m_caption->setObjectName(QStringLiteral("HintText"));

    auto *lay = new QVBoxLayout(this);
    lay->setContentsMargins(16, 14, 16, 14);
    lay->setSpacing(8);
    lay->addWidget(m_title);
    lay->addWidget(m_value);
    lay->addWidget(m_bar);
    lay->addWidget(m_caption);
}

void MetricCard::setMetric(const QString &title, const QString &value, const QString &unit,
                           double progress, const QColor &color)
{
    m_title->setText(title);
    m_value->setText(value);
    m_caption->setText(unit);

    if (progress < 0) {
        m_bar->hide();
    } else {
        m_bar->show();
        m_bar->setValue(qBound(0, qRound(progress * 100.0), 100));
        m_bar->setStyleSheet(QStringLiteral(
            "QProgressBar#MetricBar { background:#EEF1F5; border:none; border-radius:4px; max-height:8px; }"
            "QProgressBar#MetricBar::chunk { background:%1; border-radius:4px; }").arg(color.name()));
    }
}

void MetricCard::setCaption(const QString &text)
{
    m_caption->setText(text);
}
