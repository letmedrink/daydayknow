import pytest

from app.db.graph_store import InMemoryGraphStore


class TestNodeDetail:

    @pytest.mark.asyncio
    async def test_node_with_neighbors(self):
        store = InMemoryGraphStore()
        n1 = await store.create_node(user_id="u1", name="Hub")
        n2 = await store.create_node(user_id="u1", name="Leaf1")
        n3 = await store.create_node(user_id="u1", name="Leaf2")
        await store.create_edge(user_id="u1", from_node_id=n1["id"], to_node_id=n2["id"], relation_type="r")
        await store.create_edge(user_id="u1", from_node_id=n1["id"], to_node_id=n3["id"], relation_type="r")

        result = await store.get_node_with_neighbors(n1["id"])
        assert result is not None
        assert result["node"]["name"] == "Hub"
        assert len(result["neighbors"]) == 2
        assert len(result["edges"]) == 2
        neighbor_names = {n["name"] for n in result["neighbors"]}
        assert neighbor_names == {"Leaf1", "Leaf2"}

    @pytest.mark.asyncio
    async def test_node_not_found(self):
        store = InMemoryGraphStore()
        result = await store.get_node_with_neighbors("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_isolated_node(self):
        store = InMemoryGraphStore()
        n = await store.create_node(user_id="u1", name="Isolated")
        result = await store.get_node_with_neighbors(n["id"])
        assert result["node"]["name"] == "Isolated"
        assert result["neighbors"] == []
        assert result["edges"] == []


class TestConversationSearch:

    @pytest.mark.asyncio
    async def test_search_by_title(self):
        store = InMemoryGraphStore()
        await store.create_conversation(user_id="u1", title="Python 学习")
        await store.create_conversation(user_id="u1", title="JavaScript 基础")
        await store.create_conversation(user_id="u1", title="Python 进阶")

        results = await store.search_conversations(user_id="u1", query="Python")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self):
        store = InMemoryGraphStore()
        await store.create_conversation(user_id="u1", title="Docker 实战")

        results = await store.search_conversations(user_id="u1", query="docker")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_respects_user(self):
        store = InMemoryGraphStore()
        await store.create_conversation(user_id="u1", title="Shared Title")
        await store.create_conversation(user_id="u2", title="Shared Title")

        results = await store.search_conversations(user_id="u1", query="Shared")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_limit(self):
        store = InMemoryGraphStore()
        for i in range(10):
            await store.create_conversation(user_id="u1", title=f"Chat {i}")

        results = await store.search_conversations(user_id="u1", query="Chat", limit=3)
        assert len(results) == 3
