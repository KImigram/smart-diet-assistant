#include "RecognitionService.h"

#include <QBuffer>
#include <QFile>
#include <QImage>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>

#include "ApiClient.h"

RecognitionService &RecognitionService::instance()
{
    static RecognitionService s;
    return s;
}

RecognitionService::RecognitionService(QObject *parent)
    : QObject(parent)
{
}

void RecognitionService::recognize(const QString &imagePath, int userId)
{
    QImage img(imagePath);
    if (img.isNull()) {
        emit error(QStringLiteral("无法读取图片: %1").arg(imagePath));
        return;
    }

    // 优先直传原文件：≤5MB 的原图不经任何压缩，识别效果与 test_api 一致
    // （JPEG 有损压缩会破坏酱汁/猪蹄等深色纹理，导致识别漂移，如"酱焖猪蹄→红烧肉"；
    //   实测 1.31MB 的 PNG 原图直传识别"酱焖猪蹄"，压缩后却变"红烧肉"）
    QByteArray ba;
    const int kDirectMax = 2 * 1024 * 1024;   // 直传上限 2MB（原样上传，保识别精度）
    const int kCompressMax = 1 * 1024 * 1024; // 超过 2MB 才压缩，压缩目标 1MB
    QFile raw(imagePath);
    if (raw.open(QIODevice::ReadOnly) && raw.size() <= kDirectMax) {
        ba = raw.readAll();
    } else {
        // 超过 5MB 才压缩：先缩尺寸，再降质量，循环逼近
        int maxEdge = 1600;
        int quality = 90;

        while (true) {
            QImage work = img;
            if (work.width() > maxEdge || work.height() > maxEdge)
                work = work.scaled(maxEdge, maxEdge, Qt::KeepAspectRatio, Qt::SmoothTransformation);

            ba.clear();
            QBuffer buf(&ba);
            buf.open(QIODevice::WriteOnly);
            work.save(&buf, "JPEG", quality);

            if (ba.size() <= kCompressMax)
                break;

            // 先降质量，质量到30后缩尺寸
            if (quality > 30) {
                quality -= 10;
            } else {
                maxEdge = qMax(256, static_cast<int>(maxEdge * 0.8));
                quality = 50;  // 缩尺寸后恢复中等质量
            }
            if (maxEdge <= 256 && quality <= 30)
                break;  // 兜底，极端小图也接受
        }  // while 结束
    }  // else 结束

    const QString b64 = QString::fromLatin1(ba.toBase64());

    QJsonObject body;
    body["user_id"] = userId;
    body["image_base64"] = b64;

    ApiClient::instance().postJson(
        QStringLiteral("/api/recognize"),
        body,
        [this](const QJsonDocument &doc) {
            QJsonObject obj = doc.object();
            QVector<RecognitionCandidate> candidates;
            const QJsonArray arr = obj.value("candidates").toArray();
            for (const QJsonValue &v : arr) {
                QJsonObject o = v.toObject();
                RecognitionCandidate c;
                c.name = o.value("name").toString();
                c.confidence = o.value("probability").toDouble();
                c.foodId = o.value("food_id").toInt();
                c.category = o.value("category").toString();
                c.ingredients = o.value("ingredients").toString();
                c.caloriePer100g = o.value("calorie_per_100g").toDouble();
                c.proteinPer100g = o.value("protein_per_100g").toDouble();
                c.fromCorrection = o.value("from_correction").toBool();
                candidates << c;
            }
            const bool needConfirm = obj.value("need_confirm").toBool();
            emit recognized(candidates, needConfirm);
        },
        [this](const QString &err) {
            emit error(QStringLiteral("识别失败: %1").arg(err));
        });
}
