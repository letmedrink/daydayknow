import pytest

from app.db.graph_store import InMemoryGraphStore


class TestUserDomains:

    @pytest.mark.asyncio
    async def test_get_domains(self):
        store = InMemoryGraphStore()
        await store.create_node(user_id="u1", name="A", domain="NLP")
        await store.create_node(user_id="u1", name="B", domain="NLP")
        await store.create_node(user_id="u1", name="C", domain="CV")

        domains = await store.get_user_domains("u1")
        assert len(domains) == 2
        assert domains[0]["name"] == "NLP"
        assert domains[0]["count"] == 2
        assert domains[1]["name"] == "CV"
        assert domains[1]["count"] == 1

    @pytest.mark.asyncio
    async def test_domains_include_uncategorized(self):
        store = InMemoryGraphStore()
        await store.create_node(user_id="u1", name="A")

        domains = await store.get_user_domains("u1")
        assert len(domains) == 1
        assert domains[0]["name"] == "未分类"

    @pytest.mark.asyncio
    async def test_domains_empty(self):
        store = InMemoryGraphStore()
        domains = await store.get_user_domains("u1")
        assert domains == []


class TestMessageSearch:

    @pytest.mark.asyncio
    async def test_search_messages(self):
        store = InMemoryGraphStore()
        conv = await store.create_conversation(user_id="u1")
        await store.add_message(conv["id"], "user", "什么是 Python？")
        await store.add_message(conv["id"], "assistant", "Python 是一种编程语言")
        await store.add_message(conv["id"], "user", "JavaScript 呢？")

        results = await store.search_messages(conv["id"], "Python")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_messages_case_insensitive(self):
        store = InMemoryGraphStore()
        conv = await store.create_conversation(user_id="u1")
        await store.add_message(conv["id"], "user", "I love DOCKER")

        results = await store.search_messages(conv["id"], "docker")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_messages_no_match(self):
        store = InMemoryGraphStore()
        conv = await store.create_conversation(user_id="u1")
        await store.add_message(conv["id"], "user", "Hello")

        results = await store.search_messages(conv["id"], "xyz")
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_messages_limit(self):
        store = InMemoryGraphStore()
        conv = await store.create_conversation(user_id="u1")
        for i in range(10):
            await store.add_message(conv["id"], "user", f"test message {i}")

        results = await store.search_messages(conv["id"], "test", limit=3)
        assert len(results) == 3
