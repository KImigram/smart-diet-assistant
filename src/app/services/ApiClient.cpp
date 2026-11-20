#include "ApiClient.h"

#include <QNetworkReply>
#include <memory>

ApiClient &ApiClient::instance()
{
    static ApiClient s;
    return s;
}

ApiClient::ApiClient(QObject *parent)
    : QObject(parent)
{
    m_nam = new QNetworkAccessManager(this);
}

QNetworkRequest ApiClient::buildRequest(const QString &path)
{
    QNetworkRequest req(QUrl(m_baseUrl + path));
    req.setHeader(QNetworkRequest::ContentTypeHeader, QStringLiteral("application/json"));
    return req;
}

void ApiClient::get(const QString &path,
                    std::function<void(const QJsonDocument &)> onSuccess,
                    std::function<void(const QString &)> onError)
{
    QNetworkReply *reply = m_nam->get(buildRequest(path));
    connect(reply, &QNetworkReply::finished, this, [reply, onSuccess, onError]() {
        const int code = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        const QByteArray data = reply->readAll();
        if (reply->error() == QNetworkReply::NoError && code >= 200 && code < 300) {
            if (onSuccess) onSuccess(QJsonDocument::fromJson(data));
        } else if (onError) {
            const QString detail = data.isEmpty() ? reply->errorString() : QString::fromUtf8(data);
            onError(QStringLiteral("HTTP %1: %2").arg(code).arg(detail));
        }
        reply->deleteLater();
    });
}

void ApiClient::postJson(const QString &path, const QJsonObject &body,
                         std::function<void(const QJsonDocument &)> onSuccess,
                         std::function<void(const QString &)> onError)
{
    const QByteArray payload = QJsonDocument(body).toJson(QJsonDocument::Compact);
    QNetworkReply *reply = m_nam->post(buildRequest(path), payload);
    connect(reply, &QNetworkReply::finished, this, [reply, onSuccess, onError]() {
        const int code = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        const QByteArray data = reply->readAll();
        if (reply->error() == QNetworkReply::NoError && code >= 200 && code < 300) {
            if (onSuccess) onSuccess(QJsonDocument::fromJson(data));
        } else if (onError) {
            const QString detail = data.isEmpty() ? reply->errorString() : QString::fromUtf8(data);
            onError(QStringLiteral("HTTP %1: %2").arg(code).arg(detail));
        }
        reply->deleteLater();
    });
}

void ApiClient::putJson(const QString &path, const QJsonObject &body,
                        std::function<void(const QJsonDocument &)> onSuccess,
                        std::function<void(const QString &)> onError)
{
    const QByteArray payload = QJsonDocument(body).toJson(QJsonDocument::Compact);
    QNetworkReply *reply = m_nam->put(buildRequest(path), payload);
    connect(reply, &QNetworkReply::finished, this, [reply, onSuccess, onError]() {
        const int code = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        const QByteArray data = reply->readAll();
        if (reply->error() == QNetworkReply::NoError && code >= 200 && code < 300) {
            if (onSuccess) onSuccess(QJsonDocument::fromJson(data));
        } else if (onError) {
            const QString detail = data.isEmpty() ? reply->errorString() : QString::fromUtf8(data);
            onError(QStringLiteral("HTTP %1: %2").arg(code).arg(detail));
        }
        reply->deleteLater();
    });
}

void ApiClient::del(const QString &path,
                    std::function<void(const QJsonDocument &)> onSuccess,
                    std::function<void(const QString &)> onError)
{
    QNetworkReply *reply = m_nam->deleteResource(buildRequest(path));
    connect(reply, &QNetworkReply::finished, this, [reply, onSuccess, onError]() {
        const int code = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        const QByteArray data = reply->readAll();
        if (reply->error() == QNetworkReply::NoError && code >= 200 && code < 300) {
            if (onSuccess) onSuccess(QJsonDocument::fromJson(data));
        } else if (onError) {
            const QString detail = data.isEmpty() ? reply->errorString() : QString::fromUtf8(data);
            onError(QStringLiteral("HTTP %1: %2").arg(code).arg(detail));
        }
        reply->deleteLater();
    });
}

void ApiClient::postSSE(const QString &path, const QJsonObject &body,
                        std::function<void(const QString &chunk)> onChunk,
                        std::function<void(const QString &fullText)> onDone,
                        std::function<void(const QString &)> onError)
{
    const QByteArray payload = QJsonDocument(body).toJson(QJsonDocument::Compact);
    QNetworkReply *reply = m_nam->post(buildRequest(path), payload);

    // Shared ownership lets readyRead and finished safely use the same state.
    auto fullText = std::make_shared<QString>();
    auto buffer = std::make_shared<QByteArray>();

    connect(reply, &QNetworkReply::readyRead, this, [reply, onChunk, fullText, buffer]() {
        buffer->append(reply->readAll());
        while (true) {
            const int idx = buffer->indexOf("\n\n");
            if (idx < 0) break;
            const QByteArray block = buffer->left(idx);
            buffer->remove(0, idx + 2);
            for (const QByteArray &line : block.split('\n')) {
                const QByteArray trimmed = line.trimmed();
                if (!trimmed.startsWith("data: ")) continue;
                const QByteArray data = trimmed.mid(6);
                if (data == "[DONE]") continue;
                const QJsonDocument doc = QJsonDocument::fromJson(data);
                if (!doc.isObject()) continue;
                const QString content = doc.object().value("content").toString();
                if (content.isEmpty()) continue;
                fullText->append(content);
                if (onChunk) onChunk(content);
            }
        }
    });

    // Handle success and failure in one terminal callback. QNetworkReply emits
    // finished after errorOccurred, so separate cleanup handlers can run twice.
    connect(reply, &QNetworkReply::finished, this,
            [reply, onDone, onError, fullText, buffer]() {
        Q_UNUSED(buffer);
        if (reply->error() == QNetworkReply::NoError) {
            if (onDone) onDone(*fullText);
        } else if (onError) {
            onError(reply->errorString());
        }
        reply->deleteLater();
    });
}

