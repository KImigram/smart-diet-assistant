#include "MainWindow.h"

#include <QButtonGroup>
#include <QDate>
#include <QFrame>
#include <QHBoxLayout>
#include <QLabel>
#include <QPushButton>
#include <QStackedWidget>
#include <QStatusBar>
#include <QVBoxLayout>

#include "../config.h"
#include "../services/ProfileService.h"
#include "ChatPage.h"
#include "ExercisePage.h"
#include "ProfileDialog.h"
#include "RecognitionPage.h"
#include "RecordsPage.h"
#include "StatsPage.h"

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
{
    setWindowTitle(AppConfig::kAppName);
    resize(1280, 820);
    setMinimumSize(1120, 720);

    auto *central = new QWidget(this);
    auto *root = new QHBoxLayout(central);
    root->setContentsMargins(0, 0, 0, 0);
    root->setSpacing(0);
    root->addWidget(buildSidebar());
    root->addWidget(buildContent(), 1);
    setCentralWidget(central);

    statusBar()->setSizeGripEnabled(false);
    refreshAll();

    // 注册档案/体重变更回调：任何入口改了体重或档案，侧边栏实时同步
    ProfileService::instance().setOnChanged([this]() { updateUserCard(); });

    // 从后端加载用户档案（昵称/身高/体重/目标热量等），加载后刷新侧边栏
    ProfileService::instance().loadFromBackend([this](bool ok) {
        Q_UNUSED(ok);
        updateUserCard();
        statusBar()->showMessage(
            QStringLiteral("当前用户：%1    今天：%2")
                .arg(ProfileService::instance().nickname(),
                     QDate::currentDate().toString(QStringLiteral("yyyy-MM-dd dddd"))));
    });
}

QWidget *MainWindow::buildSidebar()
{
    auto *sidebar = new QFrame(this);
    sidebar->setObjectName(QStringLiteral("Sidebar"));
    sidebar->setFixedWidth(230);
    auto *lay = new QVBoxLayout(sidebar);
    lay->setContentsMargins(16, 22, 16, 16);
    lay->setSpacing(6);

    auto *title = new QLabel(AppConfig::kAppName, sidebar);
    title->setObjectName(QStringLiteral("AppTitle"));
    title->setWordWrap(true);
    auto *subtitle = new QLabel(QStringLiteral("日常营养管理助手 · 演示版"), sidebar);
    subtitle->setObjectName(QStringLiteral("AppSubtitle"));
    lay->addWidget(title);
    lay->addWidget(subtitle);
    lay->addSpacing(18);

    // 导航按钮
    auto *group = new QButtonGroup(this);
    group->setExclusive(true);
    const QStringList navNames = {
        QStringLiteral("菜品识别"),
        QStringLiteral("饮食记录"),
        QStringLiteral("统计报告"),
        QStringLiteral("AI 助手"),
        QStringLiteral("运动教练"),
    };
    for (int i = 0; i < navNames.size(); ++i) {
        auto *btn = new QPushButton(navNames.at(i), sidebar);
        btn->setObjectName(QStringLiteral("NavButton"));
        btn->setCheckable(true);
        btn->setCursor(Qt::PointingHandCursor);
        group->addButton(btn, i);
        lay->addWidget(btn);
        if (i == 0)
            btn->setChecked(true);
    }
    connect(group, QOverload<int>::of(&QButtonGroup::idClicked),
            this, &MainWindow::onNavClicked);

    lay->addStretch(1);

    // 用户卡片
    auto *userCard = new QFrame(sidebar);
    userCard->setObjectName(QStringLiteral("UserCard"));
    auto *uLay = new QVBoxLayout(userCard);
    uLay->setContentsMargins(14, 12, 14, 12);
    uLay->setSpacing(4);
    m_userName = new QLabel(userCard);
    m_userName->setObjectName(QStringLiteral("UserName"));
    m_userMeta = new QLabel(userCard);
    m_userMeta->setObjectName(QStringLiteral("UserMeta"));
    m_userMeta->setWordWrap(true);
    m_profileBtn = new QPushButton(QStringLiteral("健康档案"), userCard);
    m_profileBtn->setObjectName(QStringLiteral("ProfileBtn"));
    m_profileBtn->setCursor(Qt::PointingHandCursor);
    uLay->addWidget(m_userName);
    uLay->addWidget(m_userMeta);
    uLay->addWidget(m_profileBtn);
    lay->addWidget(userCard);

    auto *ver = new QLabel(QStringLiteral("v%1 · 前端演示版").arg(AppConfig::kVersion), sidebar);
    ver->setObjectName(QStringLiteral("VersionLabel"));
    lay->addWidget(ver);

    connect(m_profileBtn, &QPushButton::clicked, this, &MainWindow::onProfileClicked);
    return sidebar;
}

QWidget *MainWindow::buildContent()
{
    auto *content = new QWidget(this);
    auto *lay = new QVBoxLayout(content);
    lay->setContentsMargins(0, 0, 0, 0);

    m_stack = new QStackedWidget(content);
    m_recognitionPage = new RecognitionPage(m_stack);
    m_recordsPage = new RecordsPage(m_stack);
    m_statsPage = new StatsPage(m_stack);
    m_chatPage = new ChatPage(m_stack);
    m_exercisePage = new ExercisePage(m_stack);
    m_stack->addWidget(m_recognitionPage);
    m_stack->addWidget(m_recordsPage);
    m_stack->addWidget(m_statsPage);
    m_stack->addWidget(m_chatPage);
    m_stack->addWidget(m_exercisePage);

    lay->addWidget(m_stack);
    return content;
}

void MainWindow::onNavClicked(int index)
{
    m_stack->setCurrentIndex(index);
    if (index == 1) m_recordsPage->refresh();
    else if (index == 2) m_statsPage->refresh();
    else if (index == 4) m_exercisePage->refreshToday();
}

void MainWindow::switchPage(int index)
{
    m_stack->setCurrentIndex(qBound(0, index, m_stack->count() - 1));
    if (index == 1) m_recordsPage->refresh();
    else if (index == 2) m_statsPage->refresh();
    else if (index == 4) m_exercisePage->refreshToday();
}

void MainWindow::onProfileClicked()
{
    ProfileDialog dlg(this);
    if (dlg.exec() == QDialog::Accepted) {
        dlg.apply();
        refreshAll();
    }
}

void MainWindow::updateUserCard()
{
    ProfileService &pf = ProfileService::instance();
    m_userName->setText(pf.nickname());
    m_userMeta->setText(QStringLiteral("目标 %1 kcal/天 · %2 cm / %3 kg · BMI %4")
                            .arg(qRound(pf.targetCalorie()))
                            .arg(qRound(pf.heightCm()))
                            .arg(QString::number(pf.weightKg(), 'f', 1))
                            .arg(QString::number(pf.bmi(), 'f', 1)));
}

void MainWindow::refreshAll()
{
    updateUserCard();
    m_recordsPage->refresh();
    m_statsPage->refresh();
    statusBar()->showMessage(
        QStringLiteral("当前用户：%1    今天：%2")
            .arg(ProfileService::instance().nickname(),
                 QDate::currentDate().toString(QStringLiteral("yyyy-MM-dd dddd"))));
}
