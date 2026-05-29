import json
import pytest

from app.agents.evaluation_agent import EvaluationAgent
from app.agents.context import AgentContext, Message
from app.services.llm.mock import MockLLMProvider
from app.services.llm.router import ModelRouter


class TestEvaluationAgent:
    def setup_method(self):
        ModelRouter.reset()

    def teardown_method(self):
        ModelRouter.reset()

    @pytest.mark.asyncio
    async def test_no_extraction_returns_accept(self):
        mock = MockLLMProvider()
        ModelRouter.set_provider(mock)
        agent = EvaluationAgent()
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[Message(role="user", content="test")],
        )
        result = await agent.execute(ctx)
        assert result.success is True
        assert result.data["recommendation"] == "accept"
        assert len(mock.calls) == 0

    @pytest.mark.asyncio
    async def test_good_extraction_accepts(self):
        mock = MockLLMProvider()
        ModelRouter.set_provider(mock)
        mock.default_response = json.dumps({
            "score": 85,
            "issues": [],
            "recommendation": "accept",
        })
        agent = EvaluationAgent()
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[Message(role="user", content="解释注意力机制")],
        )
        ctx.intermediate_results["extraction"] = {
            "nodes": [{"name": "注意力机制", "domain": "AI", "confidence": 0.9}],
            "edges": [],
        }
        result = await agent.execute(ctx)
        assert result.success is True
        assert result.data["score"] == 85
        assert result.data["recommendation"] == "accept"

    @pytest.mark.asyncio
    async def test_poor_extraction_retries(self):
        mock = MockLLMProvider()
        ModelRouter.set_provider(mock)
        mock.default_response = json.dumps({
            "score": 55,
            "issues": [{"type": "missing_concept", "detail": "遗漏 QKV 计算"}],
            "recommendation": "retry",
            "retry_hint": "需要提取 QKV 相关概念",
        })
        agent = EvaluationAgent()
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[Message(role="user", content="解释注意力机制")],
        )
        ctx.intermediate_results["extraction"] = {
            "nodes": [{"name": "注意力", "domain": "AI", "confidence": 0.6}],
            "edges": [],
        }
        result = await agent.execute(ctx)
        assert result.success is True
        assert result.data["recommendation"] == "retry"
        assert "retry_hint" in result.data

    @pytest.mark.asyncio
    async def test_conflict_info_included(self):
        mock = MockLLMProvider()
        ModelRouter.set_provider(mock)
        mock.default_response = json.dumps({
            "score": 70,
            "issues": [{"type": "conflict_noted", "detail": "存在语义矛盾"}],
            "recommendation": "accept",
        })
        agent = EvaluationAgent()
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[Message(role="user", content="test")],
        )
        ctx.intermediate_results["extraction"] = {
            "nodes": [{"name": "A", "domain": "AI", "confidence": 0.8}],
            "edges": [],
        }
        ctx.intermediate_results["conflict_result"] = {
            "has_conflict": True,
            "conflicts": [{"severity": "high", "detail": "A 定义矛盾"}],
        }
        result = await agent.execute(ctx)
        assert result.success is True
        # 验证 LLM 收到了冲突信息
        sent = mock.calls[0]["messages"][1]["content"]
        assert "A 定义矛盾" in sent

    @pytest.mark.asyncio
    async def test_llm_error_handled(self):
        mock = MockLLMProvider(error_on="chat_json")
        ModelRouter.set_provider(mock)
        agent = EvaluationAgent()
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[Message(role="user", content="test")],
        )
        ctx.intermediate_results["extraction"] = {
            "nodes": [{"name": "test", "domain": "AI", "confidence": 0.9}],
            "edges": [],
        }
        result = await agent.execute(ctx)
        assert result.success is False
