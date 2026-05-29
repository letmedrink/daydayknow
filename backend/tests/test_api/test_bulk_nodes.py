import pytest

from app.db.graph_store import InMemoryGraphStore


class TestBulkDeleteNodes:

    @pytest.mark.asyncio
    async def test_bulk_delete(self):
        store = InMemoryGraphStore()
        n1 = await store.create_node(user_id="u1", name="A")
        n2 = await store.create_node(user_id="u1", name="B")
        n3 = await store.create_node(user_id="u1", name="C")
        await store.create_edge(user_id="u1", from_node_id=n1["id"], to_node_id=n2["id"], relation_type="r")

        count = await store.delete_nodes_bulk("u1", [n1["id"], n3["id"]])
        assert count == 2
        assert len(await store.get_user_nodes("u1")) == 1
        # 关联边也被删除
        assert len(await store.get_user_edges("u1")) == 0

    @pytest.mark.asyncio
    async def test_bulk_delete_respects_user(self):
        store = InMemoryGraphStore()
        n1 = await store.create_node(user_id="u1", name="A")
        n2 = await store.create_node(user_id="u2", name="B")

        count = await store.delete_nodes_bulk("u1", [n1["id"], n2["id"]])
        assert count == 1  # 只能删除自己的
        assert n2["id"] in store.nodes

    @pytest.mark.asyncio
    async def test_bulk_delete_empty(self):
        store = InMemoryGraphStore()
        count = await store.delete_nodes_bulk("u1", [])
        assert count == 0
