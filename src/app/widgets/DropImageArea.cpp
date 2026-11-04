#include "DropImageArea.h"

#include <QDragEnterEvent>
#include <QDropEvent>
#include <QFileDialog>
#include <QFileInfo>
#include <QMimeData>
#include <QMouseEvent>
#include <QPainter>
#include <QUrl>

DropImageArea::DropImageArea(QWidget *parent)
    : QLabel(parent)
{
    setObjectName(QStringLiteral("dropArea"));
    setAcceptDrops(true);
    setAlignment(Qt::AlignCenter);
    setMinimumHeight(260);
    setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Expanding);
    setCursor(Qt::PointingHandCursor);
    setToolTip(QStringLiteral("点击选择图片，或拖拽图片到此处"));
}

bool DropImageArea::isImageFile(const QString &path)
{
    const QString suffix = QFileInfo(path).suffix().toLower();
    return suffix == QStringLiteral("jpg") || suffix == QStringLiteral("jpeg")
        || suffix == QStringLiteral("png") || suffix == QStringLiteral("bmp")
        || suffix == QStringLiteral("webp");
}

bool DropImageArea::loadFromPath(const QString &path)
{
    if (path.isEmpty() || !QFileInfo::exists(path))
        return false;
    QPixmap pm(path);
    if (pm.isNull())
        return false;
    m_path = path;
    m_pix = pm;
    update();
    emit imageSelected(path);
    return true;
}

void DropImageArea::clearImage()
{
    m_path.clear();
    m_pix = QPixmap();
    update();
}

void DropImageArea::paintEvent(QPaintEvent *event)
{
    Q_UNUSED(event)
    QPainter p(this);
    p.setRenderHint(QPainter::Antialiasing);

    const QRectF r = rect().adjusted(1, 1, -1, -1);

    if (!m_pix.isNull()) {
        p.setPen(QPen(QColor(0xD5, 0xDD, 0xE5), 1));
        p.setBrush(Qt::white);
        p.drawRoundedRect(r, 10, 10);
        const QPixmap scaled = m_pix.scaled(size() - QSize(16, 16),
                                            Qt::KeepAspectRatio, Qt::SmoothTransformation);
        p.drawPixmap((width() - scaled.width()) / 2, (height() - scaled.height()) / 2, scaled);
        return;
    }

    // 占位：虚线边框 + 提示文字
    QColor border = m_dragging ? QColor(0x2E, 0x9E, 0x6B) : QColor(0xC8, 0xD2, 0xDC);
    p.setPen(QPen(border, 2, Qt::DashLine));
    p.setBrush(m_dragging ? QColor(0xEA, 0xF6, 0xF0) : QColor(0xFB, 0xFC, 0xFD));
    p.drawRoundedRect(r, 12, 12);

    p.setPen(QColor(0x8A, 0x99, 0xA9));
    QFont f = font();
    f.setPointSize(11);
    p.setFont(f);
    p.drawText(rect().adjusted(0, -16, 0, -16), Qt::AlignCenter,
               QStringLiteral("点击选择图片，或拖拽图片到此处"));
    p.drawText(rect().adjusted(0, 20, 0, 20), Qt::AlignCenter,
               QStringLiteral("支持 jpg / png / bmp"));
}

void DropImageArea::dragEnterEvent(QDragEnterEvent *event)
{
    if (event->mimeData()->hasUrls()) {
        const auto urls = event->mimeData()->urls();
        if (!urls.isEmpty() && isImageFile(urls.first().toLocalFile())) {
            m_dragging = true;
            update();
            event->acceptProposedAction();
            return;
        }
    }
    event->ignore();
}

void DropImageArea::dragLeaveEvent(QDragLeaveEvent *event)
{
    m_dragging = false;
    update();
    QLabel::dragLeaveEvent(event);
}

void DropImageArea::dropEvent(QDropEvent *event)
{
    m_dragging = false;
    update();
    const auto urls = event->mimeData()->urls();
    if (!urls.isEmpty()) {
        const QString path = urls.first().toLocalFile();
        if (isImageFile(path)) {
            loadFromPath(path);
            event->acceptProposedAction();
            return;
        }
    }
    event->ignore();
}

void DropImageArea::chooseImage()
{
    const QString path = QFileDialog::getOpenFileName(
        this, QStringLiteral("选择菜品图片"), QString(),
        QStringLiteral("图片文件 (*.jpg *.jpeg *.png *.bmp);;所有文件 (*.*)"));
    if (!path.isEmpty())
        loadFromPath(path);
}

void DropImageArea::mousePressEvent(QMouseEvent *event)
{
    if (event->button() == Qt::LeftButton) {
        chooseImage();
        return;
    }
    QLabel::mousePressEvent(event);
}

void DropImageArea::resizeEvent(QResizeEvent *event)
{
    QLabel::resizeEvent(event);
    update();
}
