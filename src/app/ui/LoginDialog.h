#pragma once
// ============================================================
// 登录/注册对话框
// ============================================================
#include <QDialog>

class QLabel;
class QLineEdit;
class QPushButton;
class QStackedLayout;

class LoginDialog : public QDialog
{
    Q_OBJECT
public:
    explicit LoginDialog(QWidget *parent = nullptr);

    int userId() const { return m_userId; }
    QString username() const { return m_username; }

private slots:
    void onLogin();
    void onRegister();
    void switchMode();

private:
    void showError(const QString &msg);
    void clearError();

    QLineEdit *m_userInput = nullptr;
    QLineEdit *m_passInput = nullptr;
    QLineEdit *m_nickInput = nullptr;   // 注册时显示
    QPushButton *m_submitBtn = nullptr;
    QPushButton *m_switchBtn = nullptr;
    QLabel    *m_errorLabel = nullptr;
    QLabel    *m_nickLabel = nullptr;

    bool m_isLoginMode = true;
    int  m_userId = -1;
    QString m_username;
};
