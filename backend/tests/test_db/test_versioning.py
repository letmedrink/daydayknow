import pytest

from app.db.graph_store import InMemoryGraphStore


class TestNodeVersioning:
    @pytest.mark.asyncio
    async def test_supersede_node(self):
        store = InMemoryGraphStore()
        node = await store.create_node(
            user_id="u1", name="注意力", domain="AI", description="旧描述", confidence=0.8
        )
        result = await store.supersede_node(
            node_id=node["id"],
            new_data={"name": "注意力机制", "description": "新描述", "confidence": 0.95},
            reason="用户更正",
        )
        assert result is not None
        assert result["name"] == "注意力机制"
        assert result["description"] == "新描述"
        assert result["confidence"] == 0.95
        assert result["current_version"] == 2

        versions = await store.get_node_versions(node["id"])
        assert len(versions) == 1
        assert versions[0]["name"] == "注意力"
        assert versions[0]["superseded_reason"] == "用户更正"

    @pytest.mark.asyncio
    async def test_supersede_nonexistent_node(self):
        store = InMemoryGraphStore()
        result = await store.supersede_node("nonexistent", {"name": "new"})
        assert result is None

    @pytest.mark.asyncio
    async def test_multiple_versions(self):
        store = InMemoryGraphStore()
        node = await store.create_node(user_id="u1", name="v1", confidence=0.5)
        await store.supersede_node(node["id"], {"name": "v2", "confidence": 0.7})
        await store.supersede_node(node["id"], {"name": "v3", "confidence": 0.9})

        versions = await store.get_node_versions(node["id"])
        assert len(versions) == 2
        assert versions[0]["version"] == 1
        assert versions[1]["version"] == 2

    @pytest.mark.asyncio
    async def test_soft_delete_edges(self):
        store = InMemoryGraphStore()
        n1 = await store.create_node(user_id="u1", name="A")
        n2 = await store.create_node(user_id="u1", name="B")
        edge = await store.create_edge(
            user_id="u1", from_node_id=n1["id"], to_node_id=n2["id"], relation_type="is-a"
        )
        assert edge["strength"] > 0

        count = await store.soft_delete_edges("u1", [n1["id"]])
        assert count == 1
        assert store.edges[edge["id"]]["strength"] == 0

    @pytest.mark.asyncio
    async def test_soft_delete_only_own_edges(self):
        store = InMemoryGraphStore()
        n1 = await store.create_node(user_id="u1", name="A")
        n2 = await store.create_node(user_id="u1", name="B")
        n3 = await store.create_node(user_id="u2", name="C")
        n4 = await store.create_node(user_id="u2", name="D")

        edge_u1 = await store.create_edge(
            user_id="u1", from_node_id=n1["id"], to_node_id=n2["id"], relation_type="is-a"
        )
        edge_u2 = await store.create_edge(
            user_id="u2", from_node_id=n3["id"], to_node_id=n4["id"], relation_type="is-a"
        )

        await store.soft_delete_edges("u1", [n1["id"]])
        assert store.edges[edge_u1["id"]]["strength"] == 0
        assert store.edges[edge_u2["id"]]["strength"] > 0


class TestConversationSummaries:
    @pytest.mark.asyncio
    async def test_save_and_get_summaries(self):
        store = InMemoryGraphStore()
        await store.save_summary("conv1", start_round=1, end_round=10, summary_text="第一段摘要")
        await store.save_summary("conv1", start_round=11, end_round=20, summary_text="第二段摘要")

        summaries = await store.get_summaries("conv1")
        assert len(summaries) == 2
        assert summaries[0]["start_round"] == 1
        assert summaries[1]["start_round"] == 11

    @pytest.mark.asyncio
    async def test_empty_summaries(self):
        store = InMemoryGraphStore()
        summaries = await store.get_summaries("nonexistent")
        assert summaries == []
