#pragma once
// ============================================================
// 主窗口：左侧导航 + 右侧四个功能页（QStackedWidget）
// ============================================================
#include <QMainWindow>

class QLabel;
class QPushButton;
class QStackedWidget;
class QVBoxLayout;
class RecognitionPage;
class RecordsPage;
class StatsPage;
class ChatPage;
class ExercisePage;

class MainWindow : public QMainWindow
{
    Q_OBJECT
public:
    explicit MainWindow(QWidget *parent = nullptr);

    // 切换到指定页面（0=识别 1=记录 2=统计 3=对话），供程序化调用
    void switchPage(int index);

    void refreshAll();

private slots:
    void onProfileClicked();
    void onNavClicked(int index);

private:
    QWidget *buildSidebar();
    QWidget *buildContent();
    void updateUserCard();

    QStackedWidget   *m_stack = nullptr;
    RecognitionPage  *m_recognitionPage = nullptr;
    RecordsPage      *m_recordsPage = nullptr;
    StatsPage        *m_statsPage = nullptr;
    ChatPage         *m_chatPage = nullptr;
    ExercisePage     *m_exercisePage = nullptr;

    QLabel      *m_userName = nullptr;
    QLabel      *m_userMeta = nullptr;
    QPushButton *m_profileBtn = nullptr;
};
