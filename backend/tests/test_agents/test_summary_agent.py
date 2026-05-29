import pytest

from app.agents.summary_agent import SummaryAgent
from app.agents.context import AgentContext, Message
from app.services.llm.mock import MockLLMProvider
from app.services.llm.router import ModelRouter


def make_messages(n: int) -> list:
    """生成 n 轮对话消息。"""
    msgs = []
    for i in range(n):
        msgs.append(Message(role="user", content=f"问题 {i}"))
        msgs.append(Message(role="assistant", content=f"回答 {i}"))
    return msgs


class TestSummaryAgent:
    def setup_method(self):
        ModelRouter.reset()

    def teardown_method(self):
        ModelRouter.reset()

    @pytest.mark.asyncio
    async def test_short_conversation_no_summary(self):
        mock = MockLLMProvider()
        ModelRouter.set_provider(mock)
        agent = SummaryAgent(keep_recent=10)
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=make_messages(5),
        )
        result = await agent.execute(ctx)
        assert result.success is True
        assert result.data["compressed"] is False
        assert result.data["summaries"] == []
        assert len(mock.calls) == 0

    @pytest.mark.asyncio
    async def test_long_conversation_triggers_summary(self):
        mock = MockLLMProvider()
        mock.default_response = "这是对话摘要"
        ModelRouter.set_provider(mock)
        agent = SummaryAgent(keep_recent=10)
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=make_messages(15),
        )
        result = await agent.execute(ctx)
        assert result.success is True
        assert result.data["compressed"] is True
        assert len(result.data["summaries"]) == 1
        assert result.data["summaries"][0]["level"] == "detailed"
        assert result.data["summaries"][0]["text"] == "这是对话摘要"

    @pytest.mark.asyncio
    async def test_very_long_conversation_multi_levels(self):
        mock = MockLLMProvider()
        mock.default_response = "摘要"
        ModelRouter.set_provider(mock)
        agent = SummaryAgent(keep_recent=10)
        # 75 轮 = 150 条消息，保留 10 轮，压缩 65 轮
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=make_messages(75),
        )
        result = await agent.execute(ctx)
        assert result.success is True
        assert result.data["compressed"] is True
        # 65 轮压缩 → detailed(1-30) + medium(31-60) + brief(61-65)
        assert len(result.data["summaries"]) == 3
        levels = [s["level"] for s in result.data["summaries"]]
        assert levels == ["detailed", "medium", "brief"]

    @pytest.mark.asyncio
    async def test_llm_error_does_not_block(self):
        mock = MockLLMProvider(error_on="chat")
        ModelRouter.set_provider(mock)
        agent = SummaryAgent(keep_recent=10)
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=make_messages(15),
        )
        result = await agent.execute(ctx)
        # agent 内部 catch 了异常，返回 success=True
        assert result.success is True
        assert result.data["summaries"] == []

    def test_group_rounds(self):
        msgs = [
            Message(role="user", content="q1"),
            Message(role="assistant", content="a1"),
            Message(role="user", content="q2"),
            Message(role="assistant", content="a2"),
        ]
        rounds = SummaryAgent._group_rounds(msgs)
        assert len(rounds) == 2
        assert len(rounds[0]) == 2
        assert rounds[0][0].content == "q1"

    def test_assign_levels_detailed_only(self):
        rounds = [[], [], [], [], []]
        groups = SummaryAgent._assign_levels(rounds)
        assert len(groups) == 1
        assert groups[0]["level"] == "detailed"

    def test_assign_levels_multi(self):
        rounds = [[] for _ in range(65)]
        groups = SummaryAgent._assign_levels(rounds)
        assert len(groups) == 3
        assert groups[0]["rounds"] == (1, 30)
        assert groups[1]["rounds"] == (31, 60)
        assert groups[2]["rounds"] == (61, 65)
