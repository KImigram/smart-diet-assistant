"""对话 DAO：chat_sessions + chat_messages"""
from database.connection import execute_query, execute_update


class ChatDAO:
    @staticmethod
    def get_owned_session(session_id: int, user_id: int):
        rows = execute_query(
            "SELECT id FROM chat_sessions WHERE id = %s AND user_id = %s",
            (session_id, user_id),
        )
        return rows[0] if rows else None

    @staticmethod
    def recent_session_messages(session_id: int, limit: int = 12):
        rows = execute_query(
            "SELECT role, content FROM chat_messages WHERE session_id = %s ORDER BY id DESC LIMIT %s",
            (session_id, limit),
        )
        return list(reversed(rows))

    @staticmethod
    def create_session(user_id: int, title: str = "新对话"):
        return execute_update(
            "INSERT INTO chat_sessions (user_id, title) VALUES (%s, %s)",
            (user_id, title),
        )

    @staticmethod
    def list_sessions(user_id: int):
        sql = """
            SELECT cs.id, cs.title, cs.created_at,
                   (SELECT COUNT(*) FROM chat_messages cm
                    WHERE cm.session_id = cs.id) AS message_count
            FROM chat_sessions cs
            WHERE cs.user_id = %s ORDER BY cs.created_at DESC
        """
        return execute_query(sql, (user_id,))

    @staticmethod
    def add_message(session_id: int, role: str, content: str):
        return execute_update(
            "INSERT INTO chat_messages (session_id, role, content) VALUES (%s, %s, %s)",
            (session_id, role, content),
        )

    @staticmethod
    def list_messages(session_id: int, limit: int = 50):
        """获取会话历史消息，按时间正序"""
        sql = """
            SELECT id, role, content, created_at FROM chat_messages
            WHERE session_id = %s ORDER BY created_at ASC LIMIT %s
        """
        return execute_query(sql, (session_id, limit))

    @staticmethod
    def recent_messages(user_id: int, limit: int = 20):
        """获取用户最近的对话消息（跨会话），用于 RAG 上下文"""
        sql = """
            SELECT cm.role, cm.content, cm.created_at
            FROM chat_messages cm
            JOIN chat_sessions cs ON cm.session_id = cs.id
            WHERE cs.user_id = %s
            ORDER BY cm.created_at DESC LIMIT %s
        """
        rows = execute_query(sql, (user_id, limit))
        return list(reversed(rows))  # 正序返回
