import pytest

from app.db.graph_store import InMemoryGraphStore


@pytest.fixture
def store():
    return InMemoryGraphStore()


class TestCreateNode:
    @pytest.mark.asyncio
    async def test_returns_node_with_id(self, store):
        node = await store.create_node(user_id="u1", name="机器学习")
        assert "id" in node
        assert node["name"] == "机器学习"
        assert node["user_id"] == "u1"

    @pytest.mark.asyncio
    async def test_deduplicates_by_name(self, store):
        n1 = await store.create_node(user_id="u1", name="ML", domain="AI")
        n2 = await store.create_node(user_id="u1", name="ML", domain="CS")
        assert n1["id"] == n2["id"]
        assert n1["domain"] == "AI"  # 保留首次

    @pytest.mark.asyncio
    async def test_different_users_not_deduped(self, store):
        n1 = await store.create_node(user_id="u1", name="ML")
        n2 = await store.create_node(user_id="u2", name="ML")
        assert n1["id"] != n2["id"]


class TestCreateEdge:
    @pytest.mark.asyncio
    async def test_returns_edge_with_id(self, store):
        n1 = await store.create_node(user_id="u1", name="A")
        n2 = await store.create_node(user_id="u1", name="B")
        edge = await store.create_edge(
            user_id="u1",
            from_node_id=n1["id"],
            to_node_id=n2["id"],
            relation_type="is-a",
        )
        assert edge is not None
        assert edge["relation_type"] == "is-a"

    @pytest.mark.asyncio
    async def test_self_loop_returns_none(self, store):
        n = await store.create_node(user_id="u1", name="A")
        edge = await store.create_edge(
            user_id="u1",
            from_node_id=n["id"],
            to_node_id=n["id"],
            relation_type="is-a",
        )
        assert edge is None

    @pytest.mark.asyncio
    async def test_deduplicates_edges(self, store):
        n1 = await store.create_node(user_id="u1", name="A")
        n2 = await store.create_node(user_id="u1", name="B")
        e1 = await store.create_edge(user_id="u1", from_node_id=n1["id"], to_node_id=n2["id"], relation_type="is-a")
        e2 = await store.create_edge(user_id="u1", from_node_id=n1["id"], to_node_id=n2["id"], relation_type="is-a")
        assert e1["id"] == e2["id"]


class TestStoreExtraction:
    @pytest.mark.asyncio
    async def test_creates_nodes_and_edges(self, store):
        extraction = {
            "nodes": [
                {"name": "A", "domain": "test", "description": "d1", "confidence": 0.8},
                {"name": "B", "domain": "test", "description": "d2", "confidence": 0.9},
            ],
            "edges": [
                {"from": "A", "to": "B", "relation_type": "is-a", "description": "A是B", "strength": 0.9},
            ],
        }
        result = await store.store_extraction(user_id="u1", extraction=extraction)
        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 1
        assert result["edges"][0]["from_node_id"] == result["nodes"][0]["id"]
        assert result["edges"][0]["to_node_id"] == result["nodes"][1]["id"]

    @pytest.mark.asyncio
    async def test_skips_edge_if_node_missing(self, store):
        extraction = {
            "nodes": [{"name": "A", "domain": "test"}],
            "edges": [
                {"from": "A", "to": "C", "relation_type": "is-a"},  # C 不存在
            ],
        }
        result = await store.store_extraction(user_id="u1", extraction=extraction)
        assert len(result["nodes"]) == 1
        assert len(result["edges"]) == 0

    @pytest.mark.asyncio
    async def test_source_ref_stored(self, store):
        extraction = {
            "nodes": [{"name": "A", "domain": "test"}],
            "edges": [],
        }
        result = await store.store_extraction(user_id="u1", extraction=extraction, source_ref="conv_1")
        assert result["nodes"][0]["source_ref"] == "conv_1"


class TestQuery:
    @pytest.mark.asyncio
    async def test_get_user_nodes_filters(self, store):
        await store.create_node(user_id="u1", name="A")
        await store.create_node(user_id="u2", name="B")
        nodes = await store.get_user_nodes("u1")
        assert len(nodes) == 1
        assert nodes[0]["name"] == "A"

    @pytest.mark.asyncio
    async def test_get_user_edges_filters(self, store):
        n1 = await store.create_node(user_id="u1", name="A")
        n2 = await store.create_node(user_id="u1", name="B")
        await store.create_edge(user_id="u1", from_node_id=n1["id"], to_node_id=n2["id"], relation_type="is-a")
        edges = await store.get_user_edges("u2")
        assert len(edges) == 0
