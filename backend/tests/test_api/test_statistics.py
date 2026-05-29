import pytest

from app.db.graph_store import InMemoryGraphStore


class TestStatistics:
    """InMemoryGraphStore.get_statistics 测试。"""

    @pytest.mark.asyncio
    async def test_empty_store(self):
        store = InMemoryGraphStore()
        stats = await store.get_statistics("user1")
        assert stats["total_nodes"] == 0
        assert stats["total_edges"] == 0
        assert stats["total_conversations"] == 0
        assert stats["domains"] == {}
        assert stats["top_connected_nodes"] == []

    @pytest.mark.asyncio
    async def test_node_count(self):
        store = InMemoryGraphStore()
        await store.create_node(user_id="u1", name="A", domain="D1")
        await store.create_node(user_id="u1", name="B", domain="D2")
        await store.create_node(user_id="u2", name="C", domain="D1")

        stats = await store.get_statistics("u1")
        assert stats["total_nodes"] == 2

    @pytest.mark.asyncio
    async def test_edge_count(self):
        store = InMemoryGraphStore()
        n1 = await store.create_node(user_id="u1", name="A")
        n2 = await store.create_node(user_id="u1", name="B")
        n3 = await store.create_node(user_id="u1", name="C")
        await store.create_edge(user_id="u1", from_node_id=n1["id"], to_node_id=n2["id"], relation_type="related")
        await store.create_edge(user_id="u1", from_node_id=n1["id"], to_node_id=n3["id"], relation_type="related")

        stats = await store.get_statistics("u1")
        assert stats["total_edges"] == 2

    @pytest.mark.asyncio
    async def test_domain_distribution(self):
        store = InMemoryGraphStore()
        await store.create_node(user_id="u1", name="A", domain="NLP")
        await store.create_node(user_id="u1", name="B", domain="NLP")
        await store.create_node(user_id="u1", name="C", domain="CV")
        await store.create_node(user_id="u1", name="D")

        stats = await store.get_statistics("u1")
        assert stats["domains"]["NLP"] == 2
        assert stats["domains"]["CV"] == 1
        assert stats["domains"]["未分类"] == 1

    @pytest.mark.asyncio
    async def test_top_connected_nodes(self):
        store = InMemoryGraphStore()
        n1 = await store.create_node(user_id="u1", name="Hub")
        n2 = await store.create_node(user_id="u1", name="Node2")
        n3 = await store.create_node(user_id="u1", name="Node3")
        n4 = await store.create_node(user_id="u1", name="Node4")
        # Hub 连接 3 个节点
        await store.create_edge(user_id="u1", from_node_id=n1["id"], to_node_id=n2["id"], relation_type="r")
        await store.create_edge(user_id="u1", from_node_id=n1["id"], to_node_id=n3["id"], relation_type="r")
        await store.create_edge(user_id="u1", from_node_id=n1["id"], to_node_id=n4["id"], relation_type="r")

        stats = await store.get_statistics("u1")
        assert stats["top_connected_nodes"][0]["name"] == "Hub"
        assert stats["top_connected_nodes"][0]["connections"] == 3

    @pytest.mark.asyncio
    async def test_conversation_count(self):
        store = InMemoryGraphStore()
        await store.create_conversation(user_id="u1", title="C1")
        await store.create_conversation(user_id="u1", title="C2")
        await store.create_conversation(user_id="u2", title="C3")

        stats = await store.get_statistics("u1")
        assert stats["total_conversations"] == 2
