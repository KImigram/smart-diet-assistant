#include "ChatService.h"

#include "ApiClient.h"
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>

ChatService &ChatService::instance()
{
    static ChatService s;
    return s;
}

ChatService::ChatService(QObject *parent)
    : QObject(parent)
{
}

void ChatService::loadSessions(int userId)
{
    ApiClient::instance().get(
        QStringLiteral("/api/chat/sessions?user_id=%1").arg(userId),
        [this](const QJsonDocument &doc) {
            m_sessions.clear();
            const QJsonArray arr = doc.array();
            for (const QJsonValue &v : arr) {
                QJsonObject obj = v.toObject();
                ChatSessionInfo s;
                s.id = obj.value("id").toInt();
                s.title = obj.value("title").toString();
                s.createdAt = obj.value("created_at").toString();
                s.messageCount = obj.value("message_count").toInt();
                m_sessions.append(s);
            }
            emit sessionsLoaded(m_sessions);
        },
        [this](const QString &err) {
            emit error(QStringLiteral("加载会话失败: %1").arg(err));
        });
}

void ChatService::createSession(int userId, const QString &title)
{
    QJsonObject body;
    body["user_id"] = userId;
    body["title"] = title;
    ApiClient::instance().postJson(
        QStringLiteral("/api/chat/sessions?user_id=%1&title=%2").arg(userId).arg(title),
        body,
        [this, title](const QJsonDocument &doc) {
            int id = doc.object().value("session_id").toInt();
            emit sessionCreated(id, title);
        },
        [this](const QString &err) {
            emit error(QStringLiteral("创建会话失败: %1").arg(err));
        });
}

void ChatService::loadMessages(int sessionId)
{
    ApiClient::instance().get(
        QStringLiteral("/api/chat/sessions/%1/messages").arg(sessionId),
        [this, sessionId](const QJsonDocument &doc) {
            QVector<ChatMessageInfo> msgs;
            const QJsonArray arr = doc.array();
            for (const QJsonValue &v : arr) {
                QJsonObject obj = v.toObject();
                ChatMessageInfo m;
                m.role = obj.value("role").toString();
                m.content = obj.value("content").toString();
                msgs.append(m);
            }
            emit messagesLoaded(sessionId, msgs);
        },
        [this](const QString &err) {
            emit error(QStringLiteral("加载消息失败: %1").arg(err));
        });
}

void ChatService::sendMessage(int sessionId, const QString &message, int userId)
{
    QJsonObject body;
    body["user_id"] = userId;
    body["session_id"] = sessionId;
    body["message"] = message;

    ApiClient::instance().postSSE(
        QStringLiteral("/api/chat"),
        body,
        [this](const QString &chunk) {
            emit chunkReceived(chunk);
        },
        [this](const QString &fullText) {
            emit replyFinished(fullText);
        },
        [this](const QString &err) {
            emit error(QStringLiteral("对话失败: %1").arg(err));
        });
}
