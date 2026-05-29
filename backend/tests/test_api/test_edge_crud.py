import pytest

from app.db.graph_store import InMemoryGraphStore


class TestEdgeDelete:

    @pytest.mark.asyncio
    async def test_delete_edge(self):
        store = InMemoryGraphStore()
        n1 = await store.create_node(user_id="u1", name="A")
        n2 = await store.create_node(user_id="u1", name="B")
        edge = await store.create_edge(
            user_id="u1", from_node_id=n1["id"], to_node_id=n2["id"], relation_type="r"
        )

        assert await store.delete_edge(edge["id"]) is True
        assert len(await store.get_user_edges("u1")) == 0
        # 节点应保留
        assert len(await store.get_user_nodes("u1")) == 2

    @pytest.mark.asyncio
    async def test_delete_edge_not_found(self):
        store = InMemoryGraphStore()
        assert await store.delete_edge("nonexistent") is False


class TestEdgeUpdate:

    @pytest.mark.asyncio
    async def test_update_relation_type(self):
        store = InMemoryGraphStore()
        n1 = await store.create_node(user_id="u1", name="A")
        n2 = await store.create_node(user_id="u1", name="B")
        edge = await store.create_edge(
            user_id="u1", from_node_id=n1["id"], to_node_id=n2["id"], relation_type="old"
        )

        result = await store.update_edge(edge["id"], {"relation_type": "new"})
        assert result["relation_type"] == "new"

    @pytest.mark.asyncio
    async def test_update_strength(self):
        store = InMemoryGraphStore()
        n1 = await store.create_node(user_id="u1", name="A")
        n2 = await store.create_node(user_id="u1", name="B")
        edge = await store.create_edge(
            user_id="u1", from_node_id=n1["id"], to_node_id=n2["id"], relation_type="r", strength=1.0
        )

        result = await store.update_edge(edge["id"], {"strength": 0.5})
        assert result["strength"] == 0.5

    @pytest.mark.asyncio
    async def test_update_not_found(self):
        store = InMemoryGraphStore()
        result = await store.update_edge("nonexistent", {"strength": 0.1})
        assert result is None
