import pytest

from app.db.graph_store import InMemoryGraphStore


class TestEdgeCreate:

    @pytest.mark.asyncio
    async def test_create_edge(self):
        store = InMemoryGraphStore()
        n1 = await store.create_node(user_id="u1", name="A")
        n2 = await store.create_node(user_id="u1", name="B")

        edge = await store.create_edge(
            user_id="u1",
            from_node_id=n1["id"],
            to_node_id=n2["id"],
            relation_type="causes",
        )
        assert edge is not None
        assert edge["relation_type"] == "causes"
        assert edge["from_node_id"] == n1["id"]
        assert edge["to_node_id"] == n2["id"]

    @pytest.mark.asyncio
    async def test_create_duplicate_edge(self):
        store = InMemoryGraphStore()
        n1 = await store.create_node(user_id="u1", name="A")
        n2 = await store.create_node(user_id="u1", name="B")

        edge1 = await store.create_edge(
            user_id="u1", from_node_id=n1["id"], to_node_id=n2["id"], relation_type="r"
        )
        edge2 = await store.create_edge(
            user_id="u1", from_node_id=n1["id"], to_node_id=n2["id"], relation_type="r"
        )
        # 同一条边
        assert edge1["id"] == edge2["id"]

    @pytest.mark.asyncio
    async def test_create_self_loop(self):
        store = InMemoryGraphStore()
        n1 = await store.create_node(user_id="u1", name="A")

        edge = await store.create_edge(
            user_id="u1", from_node_id=n1["id"], to_node_id=n1["id"], relation_type="self"
        )
        assert edge is None  # 不允许自环

    @pytest.mark.asyncio
    async def test_create_edge_with_description(self):
        store = InMemoryGraphStore()
        n1 = await store.create_node(user_id="u1", name="A")
        n2 = await store.create_node(user_id="u1", name="B")

        edge = await store.create_edge(
            user_id="u1",
            from_node_id=n1["id"],
            to_node_id=n2["id"],
            relation_type="related",
            strength=0.7,
            description="描述信息",
        )
        assert edge["strength"] == 0.7
        assert edge["description"] == "描述信息"
