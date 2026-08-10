import pytest

from app.agents import chat_agent
from app.agents.chat_agent import ChatAgent
from app.storage import FileStore, WikiStore


@pytest.mark.asyncio
async def test_chat_stream_persists_only_after_success(tmp_path, monkeypatch):
    global_store = FileStore(tmp_path / "global")
    project_store = FileStore(tmp_path / "project")
    wiki_store = WikiStore(tmp_path / "project")
    conversation = project_store.create_conversation("test")

    async def fake_stream(*_args, **_kwargs):
        yield {"type": "content", "content": "answer"}
        yield {"type": "content", "content": "\nOPTIONS: next | example"}

    monkeypatch.setattr(chat_agent, "stream_llm", fake_stream)
    events = [event async for event in ChatAgent(global_store, project_store, wiki_store).chat_stream(
        "question", conversation["id"], [],
    )]

    assert [event["type"] for event in events] == ["chunk", "chunk", "options"]
    messages = project_store.get_messages(conversation["id"])
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert messages[-1]["content"] == "answer"


@pytest.mark.asyncio
async def test_chat_stream_does_not_persist_failed_turn(tmp_path, monkeypatch):
    global_store = FileStore(tmp_path / "global")
    project_store = FileStore(tmp_path / "project")
    wiki_store = WikiStore(tmp_path / "project")
    conversation = project_store.create_conversation("test")

    async def failed_stream(*_args, **_kwargs):
        yield {"type": "content", "content": "partial"}
        raise RuntimeError("upstream failed")

    monkeypatch.setattr(chat_agent, "stream_llm", failed_stream)
    with pytest.raises(RuntimeError, match="upstream failed"):
        _ = [event async for event in ChatAgent(global_store, project_store, wiki_store).chat_stream(
            "question", conversation["id"], [],
        )]
    assert project_store.get_messages(conversation["id"]) == []
