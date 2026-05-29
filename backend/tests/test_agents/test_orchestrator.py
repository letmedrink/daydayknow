import json
import pytest

from app.agents.orchestrator import PostProcessOrchestrator
from app.agents.context import AgentContext, Message
from app.services.llm.mock import MockLLMProvider
from app.services.llm.router import ModelRouter


class TestPostProcessOrchestrator:
    def setup_method(self):
        ModelRouter.reset()

    def teardown_method(self):
        ModelRouter.reset()

    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        mock = MockLLMProvider()
        mock.default_response = json.dumps({
            "nodes": [{"name": "注意力", "domain": "AI", "confidence": 0.9}],
            "edges": [],
        })
        mock.json_responses = {
            "": {"knowledge_level": {"AI": 80}, "interests": ["注意力"]},
        }
        ModelRouter.set_provider(mock)

        orchestrator = PostProcessOrchestrator()
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[Message(role="user", content="解释注意力机制")],
        )

        result = await orchestrator.run(ctx)
        assert result["extraction"] is not None
        assert len(result["extraction"]["nodes"]) == 1
        assert result["profile_data"] is not None
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_extraction_failure_does_not_block(self):
        mock = MockLLMProvider(error_on="chat_json")
        ModelRouter.set_provider(mock)

        orchestrator = PostProcessOrchestrator()
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[Message(role="user", content="test")],
        )

        result = await orchestrator.run(ctx)
        # 提取失败但不应导致整个流程崩溃
        assert result["extraction"] is None
        assert any("extraction" in e for e in result["errors"])

    @pytest.mark.asyncio
    async def test_conflict_detection_in_pipeline(self):
        mock = MockLLMProvider()
        # extraction returns nodes
        mock.default_response = json.dumps({
            "nodes": [{"name": "新概念", "domain": "AI", "confidence": 0.9}],
            "edges": [],
        })
        # conflict detection response
        mock.json_responses = {
            "新概念 (领域: AI, 置信度: 0.9)": {
                "conflicts": [
                    {"type": "semantic_contradiction", "severity": "high", "detail": "描述矛盾"}
                ],
                "has_conflict": True,
            },
        }
        ModelRouter.set_provider(mock)

        orchestrator = PostProcessOrchestrator()
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[Message(role="user", content="test")],
        )

        result = await orchestrator.run(
            ctx,
            existing_nodes=[{"id": "n1", "name": "旧概念", "domain": "AI", "description": "旧"}],
            existing_edges=[],
        )
        assert result["extraction"] is not None
        assert result["conflicts"] is not None

    @pytest.mark.asyncio
    async def test_no_existing_graph_skips_conflict(self):
        mock = MockLLMProvider()
        mock.default_response = json.dumps({
            "nodes": [{"name": "test", "domain": "AI", "confidence": 0.9}],
            "edges": [],
        })
        ModelRouter.set_provider(mock)

        orchestrator = PostProcessOrchestrator()
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[Message(role="user", content="test")],
        )

        result = await orchestrator.run(ctx)
        assert result["extraction"] is not None
        # 无已有图谱 → 冲突检测返回空
        assert result["conflicts"]["has_conflict"] is False
