#pragma once
// ============================================================
// HTTP API 客户端（QNetworkAccessManager 封装）
// 所有 Service 通过它调用 Python FastAPI 后端
// 支持：GET/POST JSON、SSE 流式输出
// ============================================================
#include <QByteArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkAccessManager>
#include <QObject>
#include <QString>
#include <functional>

class ApiClient : public QObject
{
    Q_OBJECT
public:
    static ApiClient &instance();

    // 基础 URL（后端地址）
    QString baseUrl() const { return m_baseUrl; }
    void setBaseUrl(const QString &url) { m_baseUrl = url; }

    // GET 请求，回调返回 QJsonDocument
    void get(const QString &path,
             std::function<void(const QJsonDocument &)> onSuccess,
             std::function<void(const QString &)> onError = nullptr);

    // POST JSON，回调返回 QJsonDocument
    void postJson(const QString &path, const QJsonObject &body,
                  std::function<void(const QJsonDocument &)> onSuccess,
                  std::function<void(const QString &)> onError = nullptr);
    void putJson(const QString &path, const QJsonObject &body,
                 std::function<void(const QJsonDocument &)> onSuccess,
                 std::function<void(const QString &)> onError = nullptr);
    void del(const QString &path,
             std::function<void(const QJsonDocument &)> onSuccess,
             std::function<void(const QString &)> onError = nullptr);

    // POST SSE 流式请求
    // onChunk: 每收到一块文本调用
    // onDone: 流结束时调用（参数为完整文本）
    void postSSE(const QString &path, const QJsonObject &body,
                 std::function<void(const QString &chunk)> onChunk,
                 std::function<void(const QString &fullText)> onDone = nullptr,
                 std::function<void(const QString &)> onError = nullptr);

private:
    explicit ApiClient(QObject *parent = nullptr);
    QNetworkAccessManager *m_nam = nullptr;
    QString m_baseUrl = QStringLiteral("http://127.0.0.1:8001");

    QNetworkRequest buildRequest(const QString &path);
};
