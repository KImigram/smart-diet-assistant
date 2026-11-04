#pragma once
// ============================================================
// AI 营养问答服务（接入 DeepSeek + 结构化 RAG）
//
// 通过 ApiClient 调用后端 /api/chat（SSE 流式输出）
// 后端自动完成：RAG检索（用户档案+历史饮食+食物知识）→ Prompt拼接 → DeepSeek生成
// ============================================================
#include <QObject>
#include <QString>
#include <QVector>

#include "../config.h"

struct ChatSessionInfo
{
    int id = 0;
    QString title;
    QString createdAt;  // ISO格式日期时间
    int messageCount = 0;
};

struct ChatMessageInfo
{
    QString role;    // user / assistant
    QString content;
};

class ChatService : public QObject
{
    Q_OBJECT
public:
    static ChatService &instance();

    // 加载会话列表
    void loadSessions(int userId = g_currentUserId);
    // 创建新会话
    void createSession(int userId = g_currentUserId, const QString &title = QStringLiteral("新对话"));
    // 加载某会话的历史消息
    void loadMessages(int sessionId);
    // 发送消息（流式）
    void sendMessage(int sessionId, const QString &message, int userId = g_currentUserId);

    QVector<ChatSessionInfo> sessions() const { return m_sessions; }

signals:
    void sessionsLoaded(const QVector<ChatSessionInfo> &sessions);
    void sessionCreated(int sessionId, const QString &title);
    void messagesLoaded(int sessionId, const QVector<ChatMessageInfo> &messages);
    void chunkReceived(const QString &text);       // 流式逐块
    void replyFinished(const QString &fullReply);  // 完整回复
    void error(const QString &msg);

private:
    explicit ChatService(QObject *parent = nullptr);
    Q_DISABLE_COPY(ChatService)
    QVector<ChatSessionInfo> m_sessions;
};
