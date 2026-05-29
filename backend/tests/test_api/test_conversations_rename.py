import pytest

from app.db.graph_store import InMemoryGraphStore


class TestConversationRename:

    @pytest.mark.asyncio
    async def test_rename(self):
        store = InMemoryGraphStore()
        conv = await store.create_conversation(user_id="u1", title="Old Title")
        result = await store.rename_conversation(conv["id"], "New Title")
        assert result is not None
        assert result["title"] == "New Title"

    @pytest.mark.asyncio
    async def test_rename_not_found(self):
        store = InMemoryGraphStore()
        result = await store.rename_conversation("nonexistent", "Title")
        assert result is None

    @pytest.mark.asyncio
    async def test_rename_updates_timestamp(self):
        import time
        store = InMemoryGraphStore()
        conv = await store.create_conversation(user_id="u1", title="Before")
        old_time = conv["updated_at"]
        time.sleep(0.01)
        result = await store.rename_conversation(conv["id"], "After")
        assert result["updated_at"] >= old_time
