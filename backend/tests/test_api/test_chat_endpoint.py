import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.services.llm.mock import MockLLMProvider
from app.services.llm.router import ModelRouter


client = TestClient(app)


class TestChatEndpoint:
    def setup_method(self):
        ModelRouter.reset()

    def teardown_method(self):
        ModelRouter.reset()

    def test_chat_returns_sse_stream(self):
        mock = MockLLMProvider(responses={"hello": "Hi there!"})
        ModelRouter.set_provider(mock)
        mock.default_response = json.dumps({"nodes": [], "edges": []})

        response = client.post(
            "/api/chat",
            json={"message": "hello"},
            headers={"x-user-id": "test_user"},
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

    def test_chat_stream_contains_chunks_and_done(self):
        mock = MockLLMProvider(responses={"hello": "Hi there!"})
        ModelRouter.set_provider(mock)
        mock.default_response = json.dumps({"nodes": [], "edges": []})

        response = client.post(
            "/api/chat",
            json={"message": "hello"},
            headers={"x-user-id": "test_user"},
        )
        events = []
        for line in response.text.split("\n"):
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

        chunk_events = [e for e in events if e["type"] == "chunk"]
        done_events = [e for e in events if e["type"] == "done"]
        assert len(chunk_events) > 0
        assert len(done_events) == 1
        assert done_events[0]["conversation_id"]

    def test_chat_stream_content_concatenates(self):
        mock = MockLLMProvider(responses={"hello": "Hello World!"})
        ModelRouter.set_provider(mock)
        mock.default_response = json.dumps({"nodes": [], "edges": []})

        response = client.post(
            "/api/chat",
            json={"message": "hello"},
            headers={"x-user-id": "test_user"},
        )
        chunks = []
        for line in response.text.split("\n"):
            if line.startswith("data: "):
                event = json.loads(line[6:])
                if event["type"] == "chunk":
                    chunks.append(event["content"])
        assert "".join(chunks) == "Hello World!"

    def test_chat_with_history(self):
        mock = MockLLMProvider(responses={"follow up": "Reply to follow up"})
        ModelRouter.set_provider(mock)
        mock.default_response = json.dumps({"nodes": [], "edges": []})

        response = client.post(
            "/api/chat",
            json={
                "message": "follow up",
                "history": [
                    {"role": "user", "content": "first question"},
                    {"role": "assistant", "content": "first answer"},
                ],
            },
            headers={"x-user-id": "test_user"},
        )
        assert response.status_code == 200
        # 验证 messages 被正确传递（找 chat_stream 调用，跳过 router 的 chat_json）
        chat_call = next(c for c in mock.calls if c["method"] == "chat_stream")
        sent = chat_call["messages"]
        assert len(sent) >= 3  # system + 2 history + 1 current

    def test_chat_extraction_event_present(self):
        extraction = {
            "nodes": [
                {"name": "机器学习", "domain": "AI", "description": "ML", "confidence": 0.9}
            ],
            "edges": [],
        }
        mock = MockLLMProvider(responses={"hello": "response"})
        mock.default_response = json.dumps(extraction)
        ModelRouter.set_provider(mock)

        response = client.post(
            "/api/chat",
            json={"message": "hello"},
            headers={"x-user-id": "test_user"},
        )
        events = []
        for line in response.text.split("\n"):
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

        extraction_events = [e for e in events if e["type"] == "extraction"]
        assert len(extraction_events) == 1
        assert isinstance(extraction_events[0]["nodes"], list)
        assert len(extraction_events[0]["nodes"]) == 1
        assert extraction_events[0]["nodes"][0]["name"] == "机器学习"


class TestKnowledgeEndpoint:
    def test_get_knowledge_empty(self):
        response = client.get("/api/knowledge/new_user_123")
        assert response.status_code == 200
        data = response.json()
        assert data["nodes"] == []
        assert data["edges"] == []
