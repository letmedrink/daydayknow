import pytest

from app.db.graph_store import InMemoryGraphStore


class TestNodeUpdate:

    @pytest.mark.asyncio
    async def test_update_creates_new_version(self):
        store = InMemoryGraphStore()
        n = await store.create_node(user_id="u1", name="Old Name", domain="D1")

        result = await store.supersede_node(
            node_id=n["id"],
            new_data={"name": "New Name", "domain": "D2"},
            reason="test update",
        )
        assert result["name"] == "New Name"
        assert result["domain"] == "D2"
        assert result["current_version"] == 2

    @pytest.mark.asyncio
    async def test_update_preserves_history(self):
        store = InMemoryGraphStore()
        n = await store.create_node(user_id="u1", name="V1", description="desc1")

        await store.supersede_node(
            node_id=n["id"],
            new_data={"name": "V2", "description": "desc2"},
            reason="version 2",
        )
        await store.supersede_node(
            node_id=n["id"],
            new_data={"name": "V3"},
            reason="version 3",
        )

        versions = await store.get_node_versions(n["id"])
        assert len(versions) == 2
        assert versions[0]["name"] == "V1"
        assert versions[1]["name"] == "V2"
        # 当前节点是 V3
        assert store.nodes[n["id"]]["name"] == "V3"
        assert store.nodes[n["id"]]["current_version"] == 3

    @pytest.mark.asyncio
    async def test_update_not_found(self):
        store = InMemoryGraphStore()
        result = await store.supersede_node(
            node_id="nonexistent",
            new_data={"name": "X"},
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_versions_empty(self):
        store = InMemoryGraphStore()
        n = await store.create_node(user_id="u1", name="A")
        versions = await store.get_node_versions(n["id"])
        assert versions == []


class TestConversationSummaries:

    @pytest.mark.asyncio
    async def test_get_summaries(self):
        store = InMemoryGraphStore()
        conv = await store.create_conversation(user_id="u1")

        await store.save_summary(conv["id"], 1, 10, "第1-10轮摘要")
        await store.save_summary(conv["id"], 11, 20, "第11-20轮摘要")

        summaries = await store.get_summaries(conv["id"])
        assert len(summaries) == 2
        assert summaries[0]["summary_text"] == "第1-10轮摘要"
        assert summaries[1]["summary_text"] == "第11-20轮摘要"

    @pytest.mark.asyncio
    async def test_summaries_sorted(self):
        store = InMemoryGraphStore()
        conv = await store.create_conversation(user_id="u1")

        await store.save_summary(conv["id"], 11, 20, "后")
        await store.save_summary(conv["id"], 1, 10, "前")

        summaries = await store.get_summaries(conv["id"])
        assert summaries[0]["start_round"] == 1
        assert summaries[1]["start_round"] == 11
