import asyncio
import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.chat import graph_store
from app.services.llm.mock import MockLLMProvider
from app.services.llm.router import ModelRouter


client = TestClient(app)


def _run(coro):
    return asyncio.run(coro)


class TestConversationsEndpoint:
    def setup_method(self):
        ModelRouter.reset()
        graph_store.conversations.clear()
        graph_store.messages.clear()

    def test_list_conversations_empty(self):
        response = client.get(
            "/api/conversations",
            headers={"x-user-id": "test_user"},
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_list_conversations_returns_user_convs(self):
        _run(graph_store.create_conversation(user_id="test_user", title="test conv"))
        _run(graph_store.create_conversation(user_id="other_user", title="other conv"))
        response = client.get(
            "/api/conversations",
            headers={"x-user-id": "test_user"},
        )
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "test conv"

    def test_get_conversation_with_messages(self):
        conv = _run(graph_store.create_conversation(user_id="test_user", title="test"))
        _run(graph_store.add_message(conv["id"], "user", "hello"))
        _run(graph_store.add_message(conv["id"], "assistant", "hi"))
        response = client.get(
            f"/api/conversations/{conv['id']}",
            headers={"x-user-id": "test_user"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == conv["id"]
        assert len(data["messages"]) == 2
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][1]["role"] == "assistant"

    def test_get_conversation_not_found(self):
        response = client.get(
            "/api/conversations/nonexistent",
            headers={"x-user-id": "test_user"},
        )
        assert response.status_code == 404

    def test_delete_conversation(self):
        conv = _run(graph_store.create_conversation(user_id="test_user", title="to delete"))
        response = client.delete(
            f"/api/conversations/{conv['id']}",
            headers={"x-user-id": "test_user"},
        )
        assert response.status_code == 200
        result = _run(graph_store.get_conversation(conv["id"]))
        assert result is None

    def test_delete_conversation_not_found(self):
        response = client.delete(
            "/api/conversations/nonexistent",
            headers={"x-user-id": "test_user"},
        )
        assert response.status_code == 404


class TestChatPersistence:
    def setup_method(self):
        ModelRouter.reset()
        graph_store.conversations.clear()
        graph_store.messages.clear()

    def test_chat_saves_messages(self):
        mock = MockLLMProvider(responses={"hello": "Hi there!"})
        ModelRouter.set_provider(mock)
        mock.default_response = json.dumps({"nodes": [], "edges": []})

        response = client.post(
            "/api/chat",
            json={"message": "hello"},
            headers={"x-user-id": "persist_user"},
        )
        assert response.status_code == 200

        convs = _run(graph_store.list_conversations("persist_user"))
        assert len(convs) == 1
        assert convs[0]["message_count"] == 2  # user + assistant

    def test_chat_auto_titles_conversation(self):
        mock = MockLLMProvider(responses={"explain machine learning": "ML is..."})
        ModelRouter.set_provider(mock)
        mock.default_response = json.dumps({"nodes": [], "edges": []})

        client.post(
            "/api/chat",
            json={"message": "explain machine learning to me in simple terms"},
            headers={"x-user-id": "persist_user"},
        )

        convs = _run(graph_store.list_conversations("persist_user"))
        assert convs[0]["title"] == "explain machine learning to me in simple terms"

    def test_chat_continues_existing_conversation(self):
        mock = MockLLMProvider(
            responses={"hello": "Hi!", "how are you": "Good!"}
        )
        ModelRouter.set_provider(mock)
        mock.default_response = json.dumps({"nodes": [], "edges": []})

        # First message
        resp1 = client.post(
            "/api/chat",
            json={"message": "hello"},
            headers={"x-user-id": "persist_user"},
        )
        conv_id = None
        for line in resp1.text.split("\n"):
            if line.startswith("data: "):
                event = json.loads(line[6:])
                if event["type"] == "done":
                    conv_id = event["conversation_id"]

        # Second message in same conversation
        client.post(
            "/api/chat",
            json={"message": "how are you", "conversation_id": conv_id},
            headers={"x-user-id": "persist_user"},
        )

        msgs = _run(graph_store.get_messages(conv_id))
        assert len(msgs) == 4  # user, assistant, user, assistant
