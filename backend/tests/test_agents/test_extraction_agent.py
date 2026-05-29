import json
import pytest

from app.agents.extraction_agent import ExtractionAgent
from app.agents.context import AgentContext, Message
from app.services.llm.mock import MockLLMProvider
from app.services.llm.router import ModelRouter


def _make_extraction_json(nodes, edges=None):
    return json.dumps({"nodes": nodes, "edges": edges or []})


class TestExtractionAgent:
    def setup_method(self):
        ModelRouter.reset()

    def teardown_method(self):
        ModelRouter.reset()

    @pytest.mark.asyncio
    async def test_execute_returns_extraction(self):
        extraction_data = {
            "nodes": [
                {"name": "机器学习", "domain": "AI", "description": "ML", "confidence": 0.9}
            ],
            "edges": [],
        }
        # ExtractionAgent 构造的 user message 包含前缀，用 default_response 匹配
        mock = MockLLMProvider()
        mock.default_response = json.dumps(extraction_data)
        ModelRouter.set_provider(mock)
        agent = ExtractionAgent()
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[Message(role="user", content="anything")],
        )
        result = await agent.execute(ctx)
        assert result.success is True
        assert len(result.data["nodes"]) == 1
        assert result.data["nodes"][0]["name"] == "机器学习"

    @pytest.mark.asyncio
    async def test_execute_with_edges(self):
        extraction_data = {
            "nodes": [
                {"name": "A", "domain": "test", "description": "d1", "confidence": 0.8},
                {"name": "B", "domain": "test", "description": "d2", "confidence": 0.8},
            ],
            "edges": [
                {"from": "A", "to": "B", "relation_type": "is-a", "description": "A是B", "strength": 0.9}
            ],
        }
        mock = MockLLMProvider()
        mock.default_response = json.dumps(extraction_data)
        ModelRouter.set_provider(mock)
        agent = ExtractionAgent()
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[Message(role="user", content="讨论A和B")],
        )
        result = await agent.execute(ctx)
        assert result.success is True
        assert len(result.data["nodes"]) == 2
        assert len(result.data["edges"]) == 1

    @pytest.mark.asyncio
    async def test_execute_handles_malformed_json(self):
        mock = MockLLMProvider()
        mock.default_response = "not json at all"
        ModelRouter.set_provider(mock)
        agent = ExtractionAgent()
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[Message(role="user", content="x")],
        )
        result = await agent.execute(ctx)
        # Mock provider gracefully falls back to default JSON response
        assert result.success is True
        assert result.data["nodes"] == []

    @pytest.mark.asyncio
    async def test_execute_validates_nodes_field(self):
        mock = MockLLMProvider()
        mock.default_response = json.dumps({"wrong": "format"})
        ModelRouter.set_provider(mock)
        agent = ExtractionAgent()
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[Message(role="user", content="x")],
        )
        result = await agent.execute(ctx)
        assert result.success is False
        assert "nodes" in result.error
