"""Session-scoped history and persistence around the new LangChain RAG chat."""

import logging

from dao.chat_dao import ChatDAO
from rag.pipeline import stream_answer

logger = logging.getLogger(__name__)


class ChatService:
    CONTEXT_WINDOW = 12

    create_session = staticmethod(ChatDAO.create_session)
    list_sessions = staticmethod(ChatDAO.list_sessions)

    @staticmethod
    def list_messages(session_id: int):
        return ChatDAO.list_messages(session_id, limit=100)

    @staticmethod
    def send_message(user_id: int, session_id: int, message: str):
        if not ChatDAO.get_owned_session(session_id, user_id):
            raise ValueError("会话不存在或不属于当前用户")
        # Read history before inserting the current message. Repeated questions
        # are legitimate history and must not be removed by text comparison.
        history = ChatDAO.recent_session_messages(session_id, ChatService.CONTEXT_WINDOW)
        ChatDAO.add_message(session_id, "user", message)
        full_reply = []
        try:
            for chunk in stream_answer(user_id, message, history):
                full_reply.append(chunk)
                yield chunk
        except Exception:
            logger.exception("RAG chat failed for session %s", session_id)
            error = "\n【本次请求失败】检索或云端模型调用失败，请检查后端日志；未回退到旧知识库。"
            full_reply.append(error)
            yield error
        ChatDAO.add_message(session_id, "assistant", "".join(full_reply))

    @staticmethod
    def send_message_sync(user_id: int, session_id: int, message: str) -> str:
        return "".join(ChatService.send_message(user_id, session_id, message))
