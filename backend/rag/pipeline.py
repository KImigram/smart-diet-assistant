"""Online chat entry: structured data + new retrieval -> LangChain cloud model."""

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, LLM_MODEL
from rag.context_builder import build_messages, source_footer

MISSING_KEY = "尚未配置云端大模型。请在项目 .env 中填写 LLM_API_KEY，然后重启后端。"


def create_chat_model():
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL,
                      model=LLM_MODEL, temperature=0.2, max_tokens=2000,
                      timeout=60, max_retries=1)


def stream_answer(user_id: int, question: str, history: list[dict]):
    if not DEEPSEEK_API_KEY:
        yield MISSING_KEY
        return
    from services.rag_service import RAGService
    context = RAGService.retrieve(user_id, question)
    messages = build_messages(context, question, history)
    for chunk in create_chat_model().stream(messages):
        if isinstance(chunk.content, str) and chunk.content:
            yield chunk.content
    footer = source_footer(context)
    if footer:
        yield footer


def answer(user_id: int, question: str, history: list[dict]) -> str:
    return "".join(stream_answer(user_id, question, history))
