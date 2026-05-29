import json
import pytest

from app.agents.conflict_agent import ConflictAgent
from app.agents.context import AgentContext, Message
from app.services.llm.mock import MockLLMProvider
from app.services.llm.router import ModelRouter


class TestConflictAgent:
    def setup_method(self):
        ModelRouter.reset()

    def teardown_method(self):
        ModelRouter.reset()

    @pytest.mark.asyncio
    async def test_no_extraction_returns_no_conflict(self):
        mock = MockLLMProvider()
        ModelRouter.set_provider(mock)
        agent = ConflictAgent()
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[Message(role="user", content="test")],
        )
        result = await agent.execute(ctx)
        assert result.success is True
        assert result.data["has_conflict"] is False
        assert len(mock.calls) == 0

    @pytest.mark.asyncio
    async def test_no_existing_graph_returns_no_conflict(self):
        mock = MockLLMProvider()
        ModelRouter.set_provider(mock)
        agent = ConflictAgent()
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[Message(role="user", content="test")],
        )
        ctx.intermediate_results["extraction"] = {
            "nodes": [{"name": "注意力", "domain": "AI", "confidence": 0.9}],
            "edges": [],
        }
        result = await agent.execute(ctx)
        assert result.success is True
        assert result.data["has_conflict"] is False
        assert len(mock.calls) == 0

    @pytest.mark.asyncio
    async def test_detects_conflict(self):
        mock = MockLLMProvider()
        ModelRouter.set_provider(mock)
        mock.default_response = json.dumps({
            "conflicts": [
                {
                    "type": "semantic_contradiction",
                    "new_node": "注意力机制",
                    "existing_node": "注意力",
                    "detail": "描述不一致",
                    "severity": "high",
                    "suggestion": "合并或标记",
                }
            ],
            "has_conflict": True,
        })
        agent = ConflictAgent()
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[Message(role="user", content="test")],
        )
        ctx.intermediate_results["extraction"] = {
            "nodes": [{"name": "注意力机制", "domain": "AI", "description": "新的描述", "confidence": 0.9}],
            "edges": [],
        }
        ctx.metadata["existing_nodes"] = [
            {"id": "n1", "name": "注意力", "domain": "AI", "description": "旧描述"},
        ]
        ctx.metadata["existing_edges"] = []
        result = await agent.execute(ctx)
        assert result.success is True
        assert result.data["has_conflict"] is True
        assert len(result.data["conflicts"]) == 1
        assert result.data["conflicts"][0]["severity"] == "high"

    @pytest.mark.asyncio
    async def test_no_conflict_found(self):
        mock = MockLLMProvider()
        ModelRouter.set_provider(mock)
        mock.default_response = json.dumps({"conflicts": [], "has_conflict": False})
        agent = ConflictAgent()
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[Message(role="user", content="test")],
        )
        ctx.intermediate_results["extraction"] = {
            "nodes": [{"name": "CNN", "domain": "AI", "confidence": 0.9}],
            "edges": [],
        }
        ctx.metadata["existing_nodes"] = [
            {"id": "n1", "name": "RNN", "domain": "AI", "description": "循环神经网络"},
        ]
        ctx.metadata["existing_edges"] = []
        result = await agent.execute(ctx)
        assert result.success is True
        assert result.data["has_conflict"] is False

    @pytest.mark.asyncio
    async def test_llm_error_handled(self):
        mock = MockLLMProvider(error_on="chat_json")
        ModelRouter.set_provider(mock)
        agent = ConflictAgent()
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[Message(role="user", content="test")],
        )
        ctx.intermediate_results["extraction"] = {
            "nodes": [{"name": "test", "domain": "AI", "confidence": 0.9}],
            "edges": [],
        }
        ctx.metadata["existing_nodes"] = [
            {"id": "n1", "name": "existing", "domain": "AI", "description": "test"},
        ]
        ctx.metadata["existing_edges"] = []
        result = await agent.execute(ctx)
        assert result.success is False
        assert "Mock LLM error" in result.error
