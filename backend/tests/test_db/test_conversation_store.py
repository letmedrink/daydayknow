import pytest

from app.db.graph_store import InMemoryGraphStore


@pytest.fixture
def store():
    return InMemoryGraphStore()


class TestCreateConversation:
    @pytest.mark.asyncio
    async def test_returns_conversation_with_id(self, store):
        conv = await store.create_conversation(user_id="u1")
        assert "id" in conv
        assert conv["user_id"] == "u1"
        assert conv["title"] is None
        assert conv["message_count"] == 0

    @pytest.mark.asyncio
    async def test_with_title(self, store):
        conv = await store.create_conversation(user_id="u1", title="什么是机器学习")
        assert conv["title"] == "什么是机器学习"

    @pytest.mark.asyncio
    async def test_has_timestamps(self, store):
        conv = await store.create_conversation(user_id="u1")
        assert "created_at" in conv
        assert "updated_at" in conv


class TestAddMessage:
    @pytest.mark.asyncio
    async def test_returns_message_with_id(self, store):
        conv = await store.create_conversation(user_id="u1")
        msg = await store.add_message(conv["id"], "user", "hello")
        assert "id" in msg
        assert msg["role"] == "user"
        assert msg["content"] == "hello"
        assert msg["conversation_id"] == conv["id"]

    @pytest.mark.asyncio
    async def test_updates_conversation_stats(self, store):
        conv = await store.create_conversation(user_id="u1")
        await store.add_message(conv["id"], "user", "hello")
        await store.add_message(conv["id"], "assistant", "hi")
        updated = await store.get_conversation(conv["id"])
        assert updated["message_count"] == 2
        assert updated["updated_at"] != updated["created_at"]

    @pytest.mark.asyncio
    async def test_message_has_timestamp(self, store):
        conv = await store.create_conversation(user_id="u1")
        msg = await store.add_message(conv["id"], "user", "hello")
        assert "created_at" in msg


class TestListConversations:
    @pytest.mark.asyncio
    async def test_filters_by_user(self, store):
        await store.create_conversation(user_id="u1")
        await store.create_conversation(user_id="u2")
        convs = await store.list_conversations(user_id="u1")
        assert len(convs) == 1
        assert convs[0]["user_id"] == "u1"

    @pytest.mark.asyncio
    async def test_sorted_by_updated_at_desc(self, store):
        c1 = await store.create_conversation(user_id="u1", title="first")
        c2 = await store.create_conversation(user_id="u1", title="second")
        # c2 is newer
        convs = await store.list_conversations(user_id="u1")
        assert convs[0]["id"] == c2["id"]
        assert convs[1]["id"] == c1["id"]

    @pytest.mark.asyncio
    async def test_pagination(self, store):
        for i in range(5):
            await store.create_conversation(user_id="u1", title=f"conv_{i}")
        convs = await store.list_conversations(user_id="u1", limit=2, offset=0)
        assert len(convs) == 2
        convs_page2 = await store.list_conversations(user_id="u1", limit=2, offset=2)
        assert len(convs_page2) == 2


class TestGetMessages:
    @pytest.mark.asyncio
    async def test_returns_messages_in_order(self, store):
        conv = await store.create_conversation(user_id="u1")
        await store.add_message(conv["id"], "user", "hello")
        await store.add_message(conv["id"], "assistant", "hi")
        msgs = await store.get_messages(conv["id"])
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_empty_conversation(self, store):
        conv = await store.create_conversation(user_id="u1")
        msgs = await store.get_messages(conv["id"])
        assert msgs == []


class TestDeleteConversation:
    @pytest.mark.asyncio
    async def test_deletes_conversation_and_messages(self, store):
        conv = await store.create_conversation(user_id="u1")
        await store.add_message(conv["id"], "user", "hello")
        result = await store.delete_conversation(conv["id"])
        assert result is True
        assert await store.get_conversation(conv["id"]) is None
        assert await store.get_messages(conv["id"]) == []

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self, store):
        result = await store.delete_conversation("nonexistent")
        assert result is False
