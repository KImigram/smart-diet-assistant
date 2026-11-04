"""
对话管理服务
- 会话创建/列表/历史消息
- 上下文窗口管理（最近N轮）
- 串联 RAG 检索 + LLM 流式生成
- 消息持久化到 MySQL
"""
from datetime import datetime
from dao.chat_dao import ChatDAO
from services.rag_service import RAGService
from ai.llm_client import get_llm


class ChatService:
    """对话管理：会话 + 消息 + RAG + LLM"""

    # 上下文窗口：保留最近 N 条历史消息（约 N/2 轮对话）
    CONTEXT_WINDOW = 12

    @staticmethod
    def create_session(user_id: int, title: str = "新对话") -> int:
        return ChatDAO.create_session(user_id, title)

    @staticmethod
    def list_sessions(user_id: int) -> list[dict]:
        return ChatDAO.list_sessions(user_id)

    @staticmethod
    def list_messages(session_id: int) -> list[dict]:
        return ChatDAO.list_messages(session_id, limit=100)

    @staticmethod
    def send_message(user_id: int, session_id: int, message: str):
        """
        发送消息，返回流式生成器。
        流程：存用户消息 → RAG检索 → 构建Prompt → LLM流式生成 → 存AI回复
        """
        # 1. 存储用户消息
        ChatDAO.add_message(session_id, "user", message)

        # 2. 获取历史消息（上下文窗口）
        history = ChatDAO.recent_messages(user_id, limit=ChatService.CONTEXT_WINDOW)
        # 排除当前这条（刚存入的可能包含，去重）
        history_msgs = [
            {"role": m["role"], "content": m["content"]}
            for m in history if m["content"] != message
        ]

        # 3. RAG 检索 + 构建 Prompt
        messages = RAGService.build_prompt(user_id, message, history_msgs)

        # 4. LLM 流式生成
        llm = get_llm()
        full_reply = []
        for chunk in llm.chat_stream(messages):
            full_reply.append(chunk)
            yield chunk  # 逐块产出给前端

        # 5. 存储 AI 回复
        reply_text = "".join(full_reply)
        ChatDAO.add_message(session_id, "assistant", reply_text)

        # 6. 如果是新会话的第一条消息，用消息前20字更新会话标题
        sessions = ChatDAO.list_sessions(user_id)
        if sessions and sessions[0]["title"] == "新对话":
            # 不自动更新标题，保持简单
            pass

    @staticmethod
    def send_message_sync(user_id: int, session_id: int, message: str) -> str:
        """非流式版本，返回完整回复（用于测试）"""
        ChatDAO.add_message(session_id, "user", message)
        history = ChatDAO.recent_messages(user_id, limit=ChatService.CONTEXT_WINDOW)
        history_msgs = [
            {"role": m["role"], "content": m["content"]}
            for m in history if m["content"] != message
        ]
        messages = RAGService.build_prompt(user_id, message, history_msgs)
        reply = get_llm().chat(messages)
        ChatDAO.add_message(session_id, "assistant", reply)
        return reply
