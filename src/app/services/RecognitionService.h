#pragma once
// ============================================================
// 菜品识别服务（接入后端 /api/recognize）
// 异步：调用本地微调识别服务 → 匹配本地食物库 → 返回候选
// ============================================================
#include <QObject>
#include <QString>
#include <QVector>

#include "../config.h"
#include "../models/RecognitionCandidate.h"

class RecognitionService : public QObject
{
    Q_OBJECT
public:
    static RecognitionService &instance();

    // 异步识别，完成后发出 recognized 信号
    void recognize(const QString &imagePath, int userId = g_currentUserId);

signals:
    void recognized(const QVector<RecognitionCandidate> &candidates, bool needConfirm);
    void error(const QString &msg);

private:
    explicit RecognitionService(QObject *parent = nullptr);
    Q_DISABLE_COPY(RecognitionService)
};
