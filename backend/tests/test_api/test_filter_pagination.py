import pytest

from app.db.graph_store import InMemoryGraphStore


class TestDomainFilter:

    @pytest.mark.asyncio
    async def test_filter_by_domain(self):
        store = InMemoryGraphStore()
        await store.create_node(user_id="u1", name="A", domain="NLP")
        await store.create_node(user_id="u1", name="B", domain="CV")
        await store.create_node(user_id="u1", name="C", domain="NLP")

        nlp_nodes = await store.get_user_nodes("u1", domain="NLP")
        assert len(nlp_nodes) == 2

        cv_nodes = await store.get_user_nodes("u1", domain="CV")
        assert len(cv_nodes) == 1

    @pytest.mark.asyncio
    async def test_no_filter_returns_all(self):
        store = InMemoryGraphStore()
        await store.create_node(user_id="u1", name="A", domain="NLP")
        await store.create_node(user_id="u1", name="B", domain="CV")

        all_nodes = await store.get_user_nodes("u1")
        assert len(all_nodes) == 2


class TestMessagePagination:

    @pytest.mark.asyncio
    async def test_get_messages_all(self):
        store = InMemoryGraphStore()
        conv = await store.create_conversation(user_id="u1")
        for i in range(10):
            await store.add_message(conv["id"], "user", f"msg{i}")

        msgs = await store.get_messages(conv["id"])
        assert len(msgs) == 10

    @pytest.mark.asyncio
    async def test_get_messages_limit(self):
        store = InMemoryGraphStore()
        conv = await store.create_conversation(user_id="u1")
        for i in range(10):
            await store.add_message(conv["id"], "user", f"msg{i}")

        msgs = await store.get_messages(conv["id"], limit=3)
        assert len(msgs) == 3
        assert msgs[0]["content"] == "msg0"

    @pytest.mark.asyncio
    async def test_get_messages_offset(self):
        store = InMemoryGraphStore()
        conv = await store.create_conversation(user_id="u1")
        for i in range(10):
            await store.add_message(conv["id"], "user", f"msg{i}")

        msgs = await store.get_messages(conv["id"], limit=3, offset=5)
        assert len(msgs) == 3
        assert msgs[0]["content"] == "msg5"

    @pytest.mark.asyncio
    async def test_get_messages_limit_offset_combined(self):
        store = InMemoryGraphStore()
        conv = await store.create_conversation(user_id="u1")
        for i in range(20):
            await store.add_message(conv["id"], "user", f"msg{i}")

        # 最后 5 条
        msgs = await store.get_messages(conv["id"], limit=5, offset=15)
        assert len(msgs) == 5
        assert msgs[0]["content"] == "msg15"
