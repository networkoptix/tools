#include <iostream>

#include <QtCore>
#include <QtNetwork>

static const QString kServerPath = "http://localhost:7001";
static const QString kUsername = "admin";
static const QString kPassword = "qweasd123";
static const QString kEventCaption = "Test Event";
static const QString kEventDescription = "Event was triggered with a console application";

QUrl getBaseUrl()
{
    QUrl result(kServerPath);
    return result;
}

QUrl getCamerasUrl()
{
    QUrl result = getBaseUrl();
    result.setPath("/ec2/getCameras");
    return result;
}

QUrl createEventUrl(QString cameraId)
{
    QJsonArray cameraRefs;
    cameraRefs.push_back(cameraId);

    QJsonObject metadata;
    metadata["cameraRefs"] = cameraRefs;

    QUrlQuery query;
    query.addQueryItem("caption", kEventCaption);
    query.addQueryItem("description", kEventDescription);
    query.addQueryItem("metadata", QJsonDocument(metadata).toJson(QJsonDocument::Compact));

    QUrl result = getBaseUrl();
    result.setPath("/api/createEvent");
    result.setQuery(query);
    return result;
}

void addBasicAuth(QNetworkRequest* request)
{
    QString concatenated = kUsername +  ":" + kPassword;
    QByteArray data = concatenated.toLocal8Bit().toBase64();
    QString headerData = "Basic " + data;
    request->setRawHeader("Authorization", headerData.toLocal8Bit());
}

QByteArray sendRequest(QNetworkAccessManager* manager, QUrl url)
{
    QNetworkRequest request(url);
    addBasicAuth(&request);
    QScopedPointer<QNetworkReply> reply(manager->get(request));
    std::cout << "Request sent\n";

    QEventLoop loop;
    QObject::connect(reply.data(), &QNetworkReply::finished, &loop, &QEventLoop::quit);
    loop.exec();

    if (reply->error() != QNetworkReply::NoError)
    {
        std::cerr << QString("Request failed: %1").arg(reply->errorString()).toStdString() << "\n";
        return {};
    }

    return reply->readAll();
}

int main(int argc, char* argv[])
{
    QCoreApplication app(argc, argv);
    QNetworkAccessManager manager;

    QByteArray camerasData = sendRequest(&manager, getCamerasUrl());
    QJsonDocument cameras = QJsonDocument::fromJson(camerasData);
    for (auto camera: cameras.array())
    {
        const QString cameraId = camera.toObject()["id"].toString();
        sendRequest(&manager, createEventUrl(cameraId));
    }
}
