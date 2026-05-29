import pytest

from app.db.graph_store import InMemoryGraphStore


class TestGraphExport:

    @pytest.mark.asyncio
    async def test_export_json_structure(self):
        store = InMemoryGraphStore()
        n1 = await store.create_node(user_id="u1", name="A", domain="D1")
        n2 = await store.create_node(user_id="u1", name="B", domain="D2")
        await store.create_edge(user_id="u1", from_node_id=n1["id"], to_node_id=n2["id"], relation_type="r")

        data = await store.export_graph("u1")
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1
        # user_id 应被移除
        assert "user_id" not in data["nodes"][0]
        assert "user_id" not in data["edges"][0]

    @pytest.mark.asyncio
    async def test_export_empty_graph(self):
        store = InMemoryGraphStore()
        data = await store.export_graph("u1")
        assert data["nodes"] == []
        assert data["edges"] == []

    @pytest.mark.asyncio
    async def test_export_isolates_users(self):
        store = InMemoryGraphStore()
        await store.create_node(user_id="u1", name="A")
        await store.create_node(user_id="u2", name="B")

        data = await store.export_graph("u1")
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["name"] == "A"
