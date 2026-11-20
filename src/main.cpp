#include <QApplication>
#include <QFile>
#include <QFont>

#include "app/config.h"
#include "app/ui/LoginDialog.h"
#include "app/ui/MainWindow.h"

int main(int argc, char *argv[])
{
    QApplication a(argc, argv);
    a.setApplicationName(AppConfig::kAppName);
    a.setApplicationVersion(AppConfig::kVersion);
    a.setOrganizationName(AppConfig::kOrgName);

    // 显式设置全局字体：Segoe UI（主流软件标准 UI 字体）+ 微软雅黑（中文回退）
    QFont appFont;
    appFont.setFamilies({QStringLiteral("Segoe UI"), QStringLiteral("Microsoft YaHei")});
    appFont.setPointSize(10);
    appFont.setStyleStrategy(QFont::PreferAntialias);
    a.setFont(appFont);

    // 加载全局样式
    QFile qss(QStringLiteral(":/style.qss"));
    if (qss.open(QFile::ReadOnly))
        a.setStyleSheet(QString::fromUtf8(qss.readAll()));

    // 显示登录对话框
    LoginDialog login;
    if (login.exec() != QDialog::Accepted)
        return 0;

    // 登录成功，设置全局用户ID
    g_currentUserId = login.userId();

    MainWindow w;
    w.show();
    return a.exec();
}
