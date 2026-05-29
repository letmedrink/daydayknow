import pytest

from app.db.graph_store import InMemoryGraphStore


class TestDeleteNode:

    @pytest.mark.asyncio
    async def test_delete_node(self):
        store = InMemoryGraphStore()
        n1 = await store.create_node(user_id="u1", name="A")
        n2 = await store.create_node(user_id="u1", name="B")
        await store.create_edge(user_id="u1", from_node_id=n1["id"], to_node_id=n2["id"], relation_type="r")

        assert await store.delete_node(n1["id"]) is True
        assert n1["id"] not in store.nodes
        # 关联边也应被删除
        assert len(await store.get_user_edges("u1")) == 0
        # B 仍在
        assert n2["id"] in store.nodes

    @pytest.mark.asyncio
    async def test_delete_node_not_found(self):
        store = InMemoryGraphStore()
        assert await store.delete_node("nonexistent") is False


class TestBulkDeleteConversations:

    @pytest.mark.asyncio
    async def test_bulk_delete(self):
        store = InMemoryGraphStore()
        c1 = await store.create_conversation(user_id="u1", title="C1")
        c2 = await store.create_conversation(user_id="u1", title="C2")
        c3 = await store.create_conversation(user_id="u1", title="C3")

        count = await store.delete_conversations_bulk("u1", [c1["id"], c3["id"]])
        assert count == 2
        assert len(await store.list_conversations("u1")) == 1

    @pytest.mark.asyncio
    async def test_bulk_delete_respects_user(self):
        store = InMemoryGraphStore()
        c1 = await store.create_conversation(user_id="u1", title="C1")
        c2 = await store.create_conversation(user_id="u2", title="C2")

        count = await store.delete_conversations_bulk("u1", [c1["id"], c2["id"]])
        assert count == 1  # 只能删除自己的
        assert await store.get_conversation(c2["id"]) is not None

    @pytest.mark.asyncio
    async def test_bulk_delete_empty(self):
        store = InMemoryGraphStore()
        count = await store.delete_conversations_bulk("u1", [])
        assert count == 0
