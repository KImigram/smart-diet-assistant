#include "LoginDialog.h"

#include "../services/ApiClient.h"
#include <QFormLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QLineEdit>
#include <QMessageBox>
#include <QPushButton>
#include <QVBoxLayout>

LoginDialog::LoginDialog(QWidget *parent)
    : QDialog(parent)
{
    setWindowTitle(QStringLiteral("登录 - 智能营养饮食助手"));
    setFixedSize(380, 420);
    setObjectName(QStringLiteral("LoginDialog"));

    auto *root = new QVBoxLayout(this);
    root->setContentsMargins(36, 32, 36, 28);
    root->setSpacing(16);

    // 标题
    auto *title = new QLabel(QStringLiteral("智能营养饮食助手"), this);
    title->setObjectName(QStringLiteral("LoginTitle"));
    title->setAlignment(Qt::AlignCenter);
    auto *subtitle = new QLabel(QStringLiteral("AI 营养管理 · 拍照识菜 · 健康分析"), this);
    subtitle->setObjectName(QStringLiteral("LoginSubtitle"));
    subtitle->setAlignment(Qt::AlignCenter);

    // 表单
    auto *form = new QFormLayout;
    form->setSpacing(12);
    form->setLabelAlignment(Qt::AlignRight);

    m_userInput = new QLineEdit(this);
    m_userInput->setObjectName(QStringLiteral("LoginInput"));
    m_userInput->setPlaceholderText(QStringLiteral("请输入用户名"));
    m_userInput->setFixedHeight(40);

    m_passInput = new QLineEdit(this);
    m_passInput->setObjectName(QStringLiteral("LoginInput"));
    m_passInput->setPlaceholderText(QStringLiteral("请输入密码"));
    m_passInput->setEchoMode(QLineEdit::Password);
    m_passInput->setFixedHeight(40);

    m_nickLabel = new QLabel(QStringLiteral("昵称："), this);
    m_nickInput = new QLineEdit(this);
    m_nickInput->setObjectName(QStringLiteral("LoginInput"));
    m_nickInput->setPlaceholderText(QStringLiteral("选填，默认用用户名"));
    m_nickInput->setFixedHeight(40);
    m_nickLabel->hide();
    m_nickInput->hide();

    form->addRow(QStringLiteral("用户名："), m_userInput);
    form->addRow(QStringLiteral("密  码："), m_passInput);
    form->addRow(m_nickLabel, m_nickInput);

    // 错误提示
    m_errorLabel = new QLabel(this);
    m_errorLabel->setObjectName(QStringLiteral("LoginError"));
    m_errorLabel->setAlignment(Qt::AlignCenter);
    m_errorLabel->hide();

    // 按钮
    m_submitBtn = new QPushButton(QStringLiteral("登 录"), this);
    m_submitBtn->setObjectName(QStringLiteral("PrimaryBtn"));
    m_submitBtn->setFixedHeight(44);

    auto *switchRow = new QHBoxLayout;
    switchRow->addStretch(1);
    m_switchBtn = new QPushButton(QStringLiteral("没有账号？立即注册"), this);
    m_switchBtn->setObjectName(QStringLiteral("LinkBtn"));
    m_switchBtn->setFlat(true);
    switchRow->addWidget(m_switchBtn);

    root->addWidget(title);
    root->addWidget(subtitle);
    root->addSpacing(8);
    root->addLayout(form);
    root->addWidget(m_errorLabel);
    root->addWidget(m_submitBtn);
    root->addLayout(switchRow);
    root->addStretch(1);

    connect(m_submitBtn, &QPushButton::clicked, this, [this]() {
        if (m_isLoginMode) onLogin(); else onRegister();
    });
    connect(m_switchBtn, &QPushButton::clicked, this, &LoginDialog::switchMode);
    connect(m_passInput, &QLineEdit::returnPressed, this, [this]() {
        if (m_isLoginMode) onLogin(); else onRegister();
    });
}

void LoginDialog::switchMode()
{
    m_isLoginMode = !m_isLoginMode;
    clearError();
    if (m_isLoginMode) {
        setWindowTitle(QStringLiteral("登录 - 智能营养饮食助手"));
        m_submitBtn->setText(QStringLiteral("登 录"));
        m_switchBtn->setText(QStringLiteral("没有账号？立即注册"));
        m_nickLabel->hide();
        m_nickInput->hide();
    } else {
        setWindowTitle(QStringLiteral("注册 - 智能营养饮食助手"));
        m_submitBtn->setText(QStringLiteral("注 册"));
        m_switchBtn->setText(QStringLiteral("已有账号？返回登录"));
        m_nickLabel->show();
        m_nickInput->show();
    }
}

void LoginDialog::showError(const QString &msg)
{
    m_errorLabel->setText(msg);
    m_errorLabel->show();
}

void LoginDialog::clearError()
{
    m_errorLabel->clear();
    m_errorLabel->hide();
}

void LoginDialog::onLogin()
{
    const QString u = m_userInput->text().trimmed();
    const QString p = m_passInput->text();
    if (u.isEmpty() || p.isEmpty()) {
        showError(QStringLiteral("请输入用户名和密码"));
        return;
    }
    clearError();
    m_submitBtn->setEnabled(false);
    m_submitBtn->setText(QStringLiteral("登录中…"));

    QJsonObject body;
    body["username"] = u;
    body["password"] = p;
    ApiClient::instance().postJson(
        QStringLiteral("/api/auth/login"), body,
        [this, u](const QJsonDocument &doc) {
            m_userId = doc.object().value("user_id").toInt();
            m_username = u;
            accept();
        },
        [this](const QString &err) {
            showError(QStringLiteral("登录失败：%1").arg(err));
            m_submitBtn->setEnabled(true);
            m_submitBtn->setText(QStringLiteral("登 录"));
        });
}

void LoginDialog::onRegister()
{
    const QString u = m_userInput->text().trimmed();
    const QString p = m_passInput->text();
    if (u.isEmpty() || p.isEmpty()) {
        showError(QStringLiteral("请输入用户名和密码"));
        return;
    }
    if (p.length() < 4) {
        showError(QStringLiteral("密码至少4位"));
        return;
    }
    clearError();
    m_submitBtn->setEnabled(false);
    m_submitBtn->setText(QStringLiteral("注册中…"));

    QJsonObject body;
    body["username"] = u;
    body["password"] = p;
    if (!m_nickInput->text().trimmed().isEmpty())
        body["nickname"] = m_nickInput->text().trimmed();
    ApiClient::instance().postJson(
        QStringLiteral("/api/auth/register"), body,
        [this, u](const QJsonDocument &doc) {
            // 注册成功自动登录
            m_userId = doc.object().value("user_id").toInt();
            m_username = u;
            accept();
        },
        [this](const QString &err) {
            showError(QStringLiteral("注册失败：%1").arg(err));
            m_submitBtn->setEnabled(true);
            m_submitBtn->setText(QStringLiteral("注 册"));
        });
}
