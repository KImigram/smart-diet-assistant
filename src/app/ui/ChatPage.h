#pragma once
// ============================================================
// 界面 4 · AI 营养问答页
// 接入后端 DeepSeek + 结构化 RAG，SSE 流式打字机效果
// ============================================================
#include <QList>
#include <QString>
#include <QWidget>

#include "../services/ChatService.h"

class QLabel;
class QListWidget;
class QPushButton;
class QScrollArea;
class QTextEdit;
class QVBoxLayout;

class ChatPage : public QWidget
{
    Q_OBJECT
public:
    explicit ChatPage(QWidget *parent = nullptr);

protected:
    bool eventFilter(QObject *obj, QEvent *ev) override;

private slots:
    void onNewSession();
    void onSessionChanged(int row);
    void onSend();
    void onSessionsLoaded(const QVector<ChatSessionInfo> &sessions);
    void onSessionCreated(int sessionId, const QString &title);
    void onMessagesLoaded(int sessionId, const QVector<ChatMessageInfo> &messages);
    void onChunkReceived(const QString &text);
    void onReplyFinished(const QString &fullReply);
    void onError(const QString &msg);

private:
    void appendBubble(const QString &text, bool fromUser);
    void clearMessages();
    void scrollToBottom();
    void ensureTypingBubble();
    void removeTypingBubble();
    QString renderMarkdown(const QString &text);  // **加粗** -> <b></b>

    QListWidget *m_sessionList = nullptr;
    QVector<ChatSessionInfo> m_sessions;
    int m_currentSessionId = -1;

    QScrollArea *m_scroll = nullptr;
    QVBoxLayout *m_messagesLayout = nullptr;
    QWidget     *m_messagesContainer = nullptr;
    QTextEdit   *m_input = nullptr;
    QPushButton *m_send = nullptr;

    // 流式输出相关
    QLabel *m_typingLabel = nullptr;   // "正在思考…" 或流式文本
    QWidget *m_typingRow = nullptr;    // 打字气泡所在行
    QString m_streamingText;           // 当前流式累积文本
    bool m_isStreaming = false;
};
