#include "ChatPage.h"

#include <QDate>
#include <QHBoxLayout>
#include <QKeyEvent>
#include <QLabel>
#include <QListWidget>
#include <QPushButton>
#include <QRegularExpression>
#include <QScrollArea>
#include <QScrollBar>
#include <QTextEdit>
#include <QTimer>
#include <QVBoxLayout>

ChatPage::ChatPage(QWidget *parent)
    : QWidget(parent)
{
    auto *root = new QHBoxLayout(this);
    root->setContentsMargins(24, 20, 24, 16);
    root->setSpacing(14);

    // ---------- 左侧：会话列表 ----------
    auto *left = new QFrame(this);
    left->setObjectName(QStringLiteral("Card"));
    left->setFixedWidth(210);
    auto *leftLay = new QVBoxLayout(left);
    leftLay->setContentsMargins(14, 14, 14, 14);
    leftLay->setSpacing(10);

    auto *leftTitle = new QLabel(QStringLiteral("对话"), left);
    leftTitle->setObjectName(QStringLiteral("CardTitle"));
    auto *btnNew = new QPushButton(QStringLiteral("＋ 新建会话"), left);
    btnNew->setObjectName(QStringLiteral("PrimaryBtn"));

    m_sessionList = new QListWidget(left);
    m_sessionList->setObjectName(QStringLiteral("SessionList"));

    leftLay->addWidget(leftTitle);
    leftLay->addWidget(btnNew);
    leftLay->addWidget(m_sessionList, 1);

    // ---------- 右侧：对话区 ----------
    auto *right = new QWidget(this);
    auto *rightLay = new QVBoxLayout(right);
    rightLay->setContentsMargins(0, 0, 0, 0);
    rightLay->setSpacing(10);

    // 消息滚动区
    m_scroll = new QScrollArea(right);
    m_scroll->setWidgetResizable(true);
    m_scroll->setFrameShape(QFrame::NoFrame);
    m_scroll->setStyleSheet(QStringLiteral("QScrollArea { background: transparent; }"));
    m_messagesContainer = new QWidget(m_scroll);
    m_messagesLayout = new QVBoxLayout(m_messagesContainer);
    m_messagesLayout->setContentsMargins(8, 8, 8, 8);
    m_messagesLayout->setSpacing(6);
    m_messagesLayout->addStretch(1);
    m_scroll->setWidget(m_messagesContainer);
    rightLay->addWidget(m_scroll, 1);

    // 输入区
    auto *inputRow = new QHBoxLayout;
    inputRow->setSpacing(10);
    m_input = new QTextEdit(right);
    m_input->setObjectName(QStringLiteral("chatInput"));
    m_input->setPlaceholderText(QStringLiteral("输入你的营养/饮食问题，如：我今天的热量摄入够吗？（Enter 发送，Shift+Enter 换行）"));
    m_input->setMaximumHeight(90);
    m_input->setFixedHeight(72);
    m_input->installEventFilter(this);
    m_send = new QPushButton(QStringLiteral("发送"), right);
    m_send->setObjectName(QStringLiteral("btnSend"));
    m_send->setFixedWidth(96);
    m_send->setFixedHeight(72);
    inputRow->addWidget(m_input, 1);
    inputRow->addWidget(m_send);
    rightLay->addLayout(inputRow);

    root->addWidget(left);
    root->addWidget(right, 1);

    // 信号连接
    connect(btnNew, &QPushButton::clicked, this, &ChatPage::onNewSession);
    connect(m_sessionList, &QListWidget::currentRowChanged, this, &ChatPage::onSessionChanged);
    connect(m_send, &QPushButton::clicked, this, &ChatPage::onSend);
    connect(m_input, &QTextEdit::textChanged, this, [this]() {
        m_send->setEnabled(!m_input->toPlainText().trimmed().isEmpty() && !m_isStreaming);
    });

    // 连接 ChatService 信号
    ChatService &cs = ChatService::instance();
    connect(&cs, &ChatService::sessionsLoaded, this, &ChatPage::onSessionsLoaded);
    connect(&cs, &ChatService::sessionCreated, this, &ChatPage::onSessionCreated);
    connect(&cs, &ChatService::messagesLoaded, this, &ChatPage::onMessagesLoaded);
    connect(&cs, &ChatService::chunkReceived, this, &ChatPage::onChunkReceived);
    connect(&cs, &ChatService::replyFinished, this, &ChatPage::onReplyFinished);
    connect(&cs, &ChatService::error, this, &ChatPage::onError);

    m_send->setEnabled(false);

    // 加载会话列表
    cs.loadSessions();
}

void ChatPage::onNewSession()
{
    const QString title = QDate::currentDate().toString(QStringLiteral("yyyy-MM-dd"));
    ChatService::instance().createSession(1, title);
}

void ChatPage::onSessionCreated(int sessionId, const QString &title)
{
    ChatSessionInfo info;
    info.id = sessionId;
    info.title = title;
    m_sessions.append(info);
    m_sessionList->addItem(title);
    m_sessionList->setCurrentRow(m_sessions.size() - 1);
}

void ChatPage::onSessionsLoaded(const QVector<ChatSessionInfo> &sessions)
{
    m_sessions = sessions;
    m_sessionList->clear();
    for (const auto &s : sessions)
        m_sessionList->addItem(s.title);

    // 自动打开规则（按优先级）：
    // 1) 今天创建且有消息的最新会话（用户昨天的对话不会丢）
    // 2) 今天创建的最新会话
    // 3) 最新的非空会话
    // 4) 任意最新会话
    // 5) 都没有 → 新建当天会话
    const QString today = QDate::currentDate().toString(QStringLiteral("yyyy-MM-dd"));
    int pickRow = -1;

    for (int i = 0; i < sessions.size(); ++i) {
        if (sessions[i].createdAt.startsWith(today) && sessions[i].messageCount > 0) {
            pickRow = i;   // sessions 按时间倒序，第一条即最新
            break;
        }
    }
    if (pickRow < 0) {
        for (int i = 0; i < sessions.size(); ++i) {
            if (sessions[i].createdAt.startsWith(today)) {
                pickRow = i;
                break;
            }
        }
    }
    if (pickRow < 0) {
        for (int i = 0; i < sessions.size(); ++i) {
            if (sessions[i].messageCount > 0) {
                pickRow = i;
                break;
            }
        }
    }
    if (pickRow < 0 && !sessions.isEmpty())
        pickRow = 0;

    if (pickRow >= 0) {
        m_sessionList->setCurrentRow(pickRow);
    } else {
        // 没有会话，自动创建当天会话
        onNewSession();
    }
}

void ChatPage::onSessionChanged(int row)
{
    if (row < 0 || row >= m_sessions.size())
        return;
    m_currentSessionId = m_sessions[row].id;
    clearMessages();
    ChatService::instance().loadMessages(m_currentSessionId);
}

void ChatPage::onMessagesLoaded(int sessionId, const QVector<ChatMessageInfo> &messages)
{
    if (sessionId != m_currentSessionId)
        return;
    clearMessages();
    for (const auto &m : messages)
        appendBubble(m.content, m.role == QStringLiteral("user"));
    scrollToBottom();
}

bool ChatPage::eventFilter(QObject *obj, QEvent *ev)
{
    // Enter 发送消息（Shift+Enter 换行）
    if (obj == m_input && ev->type() == QEvent::KeyPress) {
        auto *ke = static_cast<QKeyEvent *>(ev);
        if ((ke->key() == Qt::Key_Return || ke->key() == Qt::Key_Enter)
            && !(ke->modifiers() & Qt::ShiftModifier)) {
            onSend();
            return true;
        }
    }
    return QWidget::eventFilter(obj, ev);
}

void ChatPage::onSend()
{
    const QString q = m_input->toPlainText().trimmed();
    if (q.isEmpty() || m_currentSessionId < 0 || m_isStreaming)
        return;
    m_input->clear();

    appendBubble(q, true);

    // 显示"正在思考…"气泡
    m_streamingText.clear();
    m_isStreaming = true;
    m_send->setEnabled(false);
    ensureTypingBubble();

    ChatService::instance().sendMessage(m_currentSessionId, q);
}

void ChatPage::ensureTypingBubble()
{
    if (m_typingRow)
        return;

    m_typingRow = new QWidget(m_messagesContainer);
    auto *lay = new QHBoxLayout(m_typingRow);
    lay->setContentsMargins(4, 2, 4, 2);
    lay->setSpacing(8);

    auto *bubble = new QFrame(m_typingRow);
    bubble->setObjectName(QStringLiteral("BubbleAssistant"));
    bubble->setMaximumWidth(560);
    auto *bl = new QVBoxLayout(bubble);
    bl->setContentsMargins(12, 9, 12, 9);

    m_typingLabel = new QLabel(QStringLiteral("正在思考…"), bubble);
    m_typingLabel->setObjectName(QStringLiteral("BubbleAssistantLabel"));
    m_typingLabel->setWordWrap(true);
    m_typingLabel->setTextFormat(Qt::RichText);
    m_typingLabel->setTextInteractionFlags(Qt::TextSelectableByMouse);
    m_typingLabel->setMaximumWidth(520);
    bl->addWidget(m_typingLabel);

    lay->addWidget(bubble);
    lay->addStretch(1);

    m_messagesLayout->insertWidget(m_messagesLayout->count() - 1, m_typingRow);
    scrollToBottom();
}

void ChatPage::removeTypingBubble()
{
    if (m_typingRow) {
        m_messagesLayout->removeWidget(m_typingRow);
        m_typingRow->deleteLater();
        m_typingRow = nullptr;
        m_typingLabel = nullptr;
    }
}

void ChatPage::onChunkReceived(const QString &text)
{
    m_streamingText.append(text);
    if (m_typingLabel) {
        m_typingLabel->setText(renderMarkdown(m_streamingText));
        scrollToBottom();
    }
}

void ChatPage::onReplyFinished(const QString &fullReply)
{
    m_isStreaming = false;
    removeTypingBubble();
    if (!fullReply.isEmpty())
        appendBubble(fullReply, false);
    m_send->setEnabled(!m_input->toPlainText().trimmed().isEmpty());
    scrollToBottom();
}

void ChatPage::onError(const QString &msg)
{
    m_isStreaming = false;
    removeTypingBubble();
    appendBubble(QStringLiteral("⚠ %1").arg(msg), false);
    m_send->setEnabled(true);
}

void ChatPage::appendBubble(const QString &text, bool fromUser)
{
    auto *row = new QWidget(m_messagesContainer);
    auto *lay = new QHBoxLayout(row);
    lay->setContentsMargins(4, 2, 4, 2);
    lay->setSpacing(8);

    auto *bubble = new QFrame(row);
    bubble->setObjectName(fromUser ? QStringLiteral("BubbleUser") : QStringLiteral("BubbleAssistant"));
    bubble->setMaximumWidth(560);
    auto *bl = new QVBoxLayout(bubble);
    bl->setContentsMargins(12, 9, 12, 9);
    auto *lb = new QLabel(bubble);
    lb->setObjectName(fromUser ? QStringLiteral("BubbleUserLabel") : QStringLiteral("BubbleAssistantLabel"));
    lb->setWordWrap(true);
    lb->setTextFormat(Qt::RichText);
    lb->setText(renderMarkdown(text));
    lb->setTextInteractionFlags(Qt::TextSelectableByMouse);
    lb->setMaximumWidth(520);
    bl->addWidget(lb);

    if (fromUser) {
        lay->addStretch(1);
        lay->addWidget(bubble);
    } else {
        lay->addWidget(bubble);
        lay->addStretch(1);
    }

    m_messagesLayout->insertWidget(m_messagesLayout->count() - 1, row);
    scrollToBottom();
}

void ChatPage::clearMessages()
{
    while (m_messagesLayout->count() > 1) {
        QLayoutItem *item = m_messagesLayout->takeAt(0);
        if (item->widget())
            item->widget()->deleteLater();
        delete item;
    }
    m_typingRow = nullptr;
    m_typingLabel = nullptr;
}

void ChatPage::scrollToBottom()
{
    QTimer::singleShot(0, this, [this]() {
        m_scroll->verticalScrollBar()->setValue(m_scroll->verticalScrollBar()->maximum());
    });
}

QString ChatPage::renderMarkdown(const QString &text)
{
    // 转义HTML特殊字符
    QString html = text.toHtmlEscaped();
    // **加粗** -> <b>加粗</b>
    html.replace(QRegularExpression("\\*\\*(.+?)\\*\\*"), QStringLiteral("<b>\\1</b>"));
    // 换行 -> <br>
    html.replace("\n", QStringLiteral("<br>"));
    return html;
}
