#pragma once
// ============================================================
// 图片选择/拖放区域：支持点击选择图片、拖拽图片文件到区域
// ============================================================
#include <QLabel>
#include <QPixmap>
#include <QString>

class DropImageArea : public QLabel
{
    Q_OBJECT
public:
    explicit DropImageArea(QWidget *parent = nullptr);

    // 从路径加载图片（失败返回 false）
    bool loadFromPath(const QString &path);

    // 弹出文件选择对话框并加载所选图片
    void chooseImage();

    QString imagePath() const { return m_path; }
    bool hasImage() const { return !m_pix.isNull(); }
    void clearImage();

signals:
    void imageSelected(const QString &path);

protected:
    void paintEvent(QPaintEvent *event) override;
    void dragEnterEvent(QDragEnterEvent *event) override;
    void dragLeaveEvent(QDragLeaveEvent *event) override;
    void dropEvent(QDropEvent *event) override;
    void mousePressEvent(QMouseEvent *event) override;
    void resizeEvent(QResizeEvent *event) override;

private:
    static bool isImageFile(const QString &path);

    QString m_path;
    QPixmap m_pix;
    bool    m_dragging = false;
};
