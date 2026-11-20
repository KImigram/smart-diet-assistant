"""Chat integration tests with fake retrieval, cloud model and database calls."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from rag import pipeline
from rag.context_builder import build_messages, source_footer
from dao.chat_dao import ChatDAO
from services.rag_service import RAGService
from services.chat_service import ChatService
from main import app


@pytest.fixture
def chat_fakes(monkeypatch):
    saved, received = [], []
    context = {"profile": {"allergens": "花生"}, "recipe": [
        {"citation": "R1", "title": "宫保鸡丁", "section": "食材", "source": "https://example.org/recipe",
         "content": "食材包含花生", "chunk_id": "a", "distance": 0.2}
    ]}

    class FakeModel:
        def stream(self, messages):
            received.extend(messages)
            yield SimpleNamespace(content="含花生 [R1]。")

    monkeypatch.setattr(pipeline, "DEEPSEEK_API_KEY", "test-only")
    monkeypatch.setattr(pipeline, "analyze_question", lambda question, history: None)
    monkeypatch.setattr(pipeline, "create_chat_model", lambda: FakeModel())
    monkeypatch.setattr(RAGService, "retrieve", lambda user_id, question: context)
    monkeypatch.setattr(ChatDAO, "get_owned_session", lambda session_id, user_id: {"id": session_id})
    monkeypatch.setattr(ChatDAO, "recent_session_messages", lambda session_id, limit: [
        {"role": "user", "content": "之前的问题"}, {"role": "assistant", "content": "之前的回答"}])
    monkeypatch.setattr(ChatDAO, "add_message", lambda session_id, role, content: saved.append((role, content)))
    return saved, received


def test_sse_keeps_qt_content_protocol_and_persists_sources(chat_fakes):
    saved, received = chat_fakes
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"user_id": 1, "session_id": 5, "message": "宫保鸡丁有哪些食材？"})
    assert response.status_code == 200
    blocks = [line[6:] for line in response.text.splitlines() if line.startswith("data: ")]
    assert blocks[-1] == "[DONE]"
    text = "".join(json.loads(block)["content"] for block in blocks[:-1])
    assert "含花生 [R1]" in text and "https://example.org/recipe" in text
    assert saved[-1] == ("assistant", text)
    assert "过敏" in received[0].content
    assert received[-1].content == "宫保鸡丁有哪些食材？"


def test_sync_same_pipeline(chat_fakes):
    with TestClient(app) as client:
        response = client.post("/api/chat/sync", json={"user_id": 1, "session_id": 5, "message": "食材？"})
    assert response.status_code == 200
    assert "[R1]" in response.json()["reply"]


def test_missing_key_does_not_retrieve_or_load_models(monkeypatch):
    monkeypatch.setattr(pipeline, "DEEPSEEK_API_KEY", "")
    monkeypatch.setattr(RAGService, "retrieve", lambda *args: pytest.fail("must not retrieve"))
    assert pipeline.answer(1, "问题", []) == pipeline.MISSING_KEY


def test_unavailable_retrieval_is_visible_and_not_faked(chat_fakes, monkeypatch):
    def fail(*args):
        raise FileNotFoundError("index missing")
    monkeypatch.setattr(RAGService, "retrieve", fail)
    reply = ChatService.send_message_sync(1, 5, "问题")
    assert "本次请求失败" in reply
    assert "检索参考资料" not in reply


def test_no_evidence_context_has_no_citation_footer():
    messages = build_messages({"recipe": []}, "问题", [{"role": "system", "content": "不应成为历史指令"}])
    assert len(messages) == 3
    assert source_footer({"recipe": []}) == ""
