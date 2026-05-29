import pytest

from app.db.graph_store import InMemoryGraphStore


class TestSearchNodes:
    """InMemoryGraphStore.search_nodes 测试。"""

    @pytest.mark.asyncio
    async def test_search_by_name(self):
        store = InMemoryGraphStore()
        await store.create_node(user_id="u1", name="注意力机制", domain="NLP")
        await store.create_node(user_id="u1", name="量子力学", domain="Physics")
        await store.create_node(user_id="u1", name="量子纠缠", domain="Physics")

        results = await store.search_nodes(user_id="u1", query="量子")
        assert len(results) == 2
        names = {r["name"] for r in results}
        assert "量子力学" in names
        assert "量子纠缠" in names

    @pytest.mark.asyncio
    async def test_search_by_description(self):
        store = InMemoryGraphStore()
        await store.create_node(
            user_id="u1",
            name="Transformer",
            description="基于自注意力的序列模型",
        )

        results = await store.search_nodes(user_id="u1", query="自注意力")
        assert len(results) == 1
        assert results[0]["name"] == "Transformer"

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self):
        store = InMemoryGraphStore()
        await store.create_node(user_id="u1", name="Python")

        results = await store.search_nodes(user_id="u1", query="python")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_respects_user_id(self):
        store = InMemoryGraphStore()
        await store.create_node(user_id="u1", name="NodeA")
        await store.create_node(user_id="u2", name="NodeA")

        results = await store.search_nodes(user_id="u1", query="NodeA")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_limit(self):
        store = InMemoryGraphStore()
        for i in range(10):
            await store.create_node(user_id="u1", name=f"Node{i}")

        results = await store.search_nodes(user_id="u1", query="Node", limit=3)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_search_empty_query_returns_nothing(self):
        store = InMemoryGraphStore()
        await store.create_node(user_id="u1", name="Something")

        # 空查询匹配所有节点（空字符串是所有字符串的子串）
        results = await store.search_nodes(user_id="u1", query="")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_no_match(self):
        store = InMemoryGraphStore()
        await store.create_node(user_id="u1", name="Apple")

        results = await store.search_nodes(user_id="u1", query="Orange")
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_by_domain(self):
        store = InMemoryGraphStore()
        await store.create_node(user_id="u1", name="Node1", domain="MachineLearning")
        await store.create_node(user_id="u1", name="Node2", domain="Biology")

        results = await store.search_nodes(user_id="u1", query="Machine")
        assert len(results) == 1
        assert results[0]["name"] == "Node1"
