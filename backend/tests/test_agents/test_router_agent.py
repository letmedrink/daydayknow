import json
import pytest

from app.agents.router_agent import RouterAgent
from app.agents.context import AgentContext, Message
from app.services.llm.mock import MockLLMProvider
from app.services.llm.router import ModelRouter


class TestRouterAgent:
    def setup_method(self):
        ModelRouter.reset()

    def teardown_method(self):
        ModelRouter.reset()

    @pytest.mark.asyncio
    async def test_no_messages_returns_defaults(self):
        mock = MockLLMProvider()
        ModelRouter.set_provider(mock)
        agent = RouterAgent()
        ctx = AgentContext(conversation_id="c1", user_id="u1", messages=[])
        result = await agent.execute(ctx)
        assert result.success is True
        assert result.data["expert"] == "generalist"
        assert result.data["depth"] == "quick"
        # 不应调用 LLM
        assert len(mock.calls) == 0

    @pytest.mark.asyncio
    async def test_classifies_intent(self):
        mock = MockLLMProvider()
        ModelRouter.set_provider(mock)
        mock.default_response = json.dumps({"intent": "explain", "expert": "teacher", "depth": "deep"})
        agent = RouterAgent()
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[Message(role="user", content="请详细解释反向传播算法")],
        )
        result = await agent.execute(ctx)
        assert result.success is True
        assert result.data["intent"] == "explain"
        assert result.data["expert"] == "teacher"
        assert result.data["depth"] == "deep"

    @pytest.mark.asyncio
    async def test_llm_error_returns_defaults(self):
        mock = MockLLMProvider(error_on="chat_json")
        ModelRouter.set_provider(mock)
        agent = RouterAgent()
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[Message(role="user", content="hello")],
        )
        result = await agent.execute(ctx)
        # router 对失败有兜底，仍然 success=True
        assert result.success is True
        assert result.data["expert"] == "generalist"

    @pytest.mark.asyncio
    async def test_partial_response_fills_defaults(self):
        mock = MockLLMProvider()
        ModelRouter.set_provider(mock)
        # 只返回 intent，缺少 expert 和 depth
        mock.default_response = json.dumps({"intent": "quiz"})
        agent = RouterAgent()
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[Message(role="user", content="测试我一下")],
        )
        result = await agent.execute(ctx)
        assert result.success is True
        assert result.data["intent"] == "quiz"
        assert result.data["expert"] == "generalist"  # 兜底
        assert result.data["depth"] == "quick"  # 兜底
