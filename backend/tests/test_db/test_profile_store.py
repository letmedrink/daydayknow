import pytest

from app.db.graph_store import InMemoryGraphStore


@pytest.fixture
def store():
    return InMemoryGraphStore()


class TestProfileStore:
    @pytest.mark.asyncio
    async def test_save_and_get_profile(self, store):
        data = {
            "knowledge_level": {"AI": 70},
            "interests": ["机器学习", "深度学习"],
            "learning_style": "analogy",
        }
        profile = await store.save_profile("u1", data)
        assert profile["user_id"] == "u1"
        assert profile["data"]["learning_style"] == "analogy"

        fetched = await store.get_profile("u1")
        assert fetched["data"]["knowledge_level"]["AI"] == 70

    @pytest.mark.asyncio
    async def test_merge_profile_updates_values(self, store):
        await store.save_profile("u1", {
            "learning_style": "analogy",
            "interests": ["ML"],
        })
        await store.save_profile("u1", {
            "learning_style": "case",
            "interests": ["DL"],
        })
        profile = await store.get_profile("u1")
        assert profile["data"]["learning_style"] == "case"
        assert "ML" in profile["data"]["interests"]
        assert "DL" in profile["data"]["interests"]

    @pytest.mark.asyncio
    async def test_merge_profile_merges_dicts(self, store):
        await store.save_profile("u1", {
            "knowledge_level": {"AI": 50, "ML": 30},
        })
        await store.save_profile("u1", {
            "knowledge_level": {"AI": 70, "DL": 40},
        })
        profile = await store.get_profile("u1")
        assert profile["data"]["knowledge_level"]["AI"] == 70
        assert profile["data"]["knowledge_level"]["ML"] == 30
        assert profile["data"]["knowledge_level"]["DL"] == 40

    @pytest.mark.asyncio
    async def test_merge_skips_none_values(self, store):
        await store.save_profile("u1", {
            "learning_style": "analogy",
            "depth_preference": "deep",
        })
        await store.save_profile("u1", {
            "learning_style": None,
            "depth_preference": "shallow",
        })
        profile = await store.get_profile("u1")
        assert profile["data"]["learning_style"] == "analogy"
        assert profile["data"]["depth_preference"] == "shallow"

    @pytest.mark.asyncio
    async def test_get_nonexistent_profile(self, store):
        assert await store.get_profile("no_user") is None

    @pytest.mark.asyncio
    async def test_different_users_separate_profiles(self, store):
        await store.save_profile("u1", {"learning_style": "analogy"})
        await store.save_profile("u2", {"learning_style": "formula"})
        p1 = await store.get_profile("u1")
        p2 = await store.get_profile("u2")
        assert p1["data"]["learning_style"] == "analogy"
        assert p2["data"]["learning_style"] == "formula"
