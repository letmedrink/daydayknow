import pytest

from app.agents.chat_agent import ChatAgent, truncate_messages, estimate_tokens, format_profile
from app.agents.context import AgentContext, Message
from app.services.llm.mock import MockLLMProvider
from app.services.llm.router import ModelRouter


class TestTruncateMessages:
    def test_short_messages_unchanged(self):
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        result = truncate_messages(messages, max_tokens=6000)
        assert len(result) == 3

    def test_truncates_by_max_messages(self):
        messages = [{"role": "system", "content": "sys"}]
        for i in range(30):
            messages.append({"role": "user", "content": f"msg {i}"})
        result = truncate_messages(messages, max_messages=5)
        # system + last 5 user messages
        assert len(result) == 6
        assert result[1]["content"] == "msg 25"

    def test_truncates_by_token_budget(self):
        messages = [{"role": "system", "content": "sys"}]
        for i in range(10):
            messages.append({"role": "user", "content": "x" * 1000})
        result = truncate_messages(messages, max_tokens=2000)
        assert len(result) < len(messages)
        # 至少保留 1 条 chat 消息
        assert len(result) >= 2

    def test_preserves_system_message(self):
        messages = [
            {"role": "system", "content": "important system prompt"},
        ]
        for i in range(20):
            messages.append({"role": "user", "content": f"msg {i}"})
        result = truncate_messages(messages, max_messages=3)
        assert result[0]["role"] == "system"
        assert result[0]["content"] == "important system prompt"

    def test_no_system_message(self):
        messages = [
            {"role": "user", "content": "a"},
            {"role": "assistant", "content": "b"},
            {"role": "user", "content": "c"},
        ]
        result = truncate_messages(messages, max_messages=2)
        assert len(result) == 2
        assert result[0]["content"] == "b"

    def test_empty_messages(self):
        assert truncate_messages([]) == []


class TestChatAgent:
    def setup_method(self):
        ModelRouter.reset()

    def teardown_method(self):
        ModelRouter.reset()

    @pytest.mark.asyncio
    async def test_execute_returns_response(self):
        mock = MockLLMProvider(responses={"hello": "Hi there!"})
        ModelRouter.set_provider(mock)
        agent = ChatAgent()
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[Message(role="user", content="hello")],
        )
        result = await agent.execute(ctx)
        assert result.success is True
        assert result.data["response"] == "Hi there!"

    @pytest.mark.asyncio
    async def test_stream_yields_chunks(self):
        mock = MockLLMProvider(responses={"hello": "Hello World Response"})
        ModelRouter.set_provider(mock)
        agent = ChatAgent()
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[Message(role="user", content="hello")],
        )
        chunks = []
        async for chunk in agent.stream(ctx):
            chunks.append(chunk)
        assert "".join(chunks) == "Hello World Response"

    @pytest.mark.asyncio
    async def test_custom_system_prompt(self):
        mock = MockLLMProvider()
        ModelRouter.set_provider(mock)
        agent = ChatAgent(system_prompt="Custom prompt")
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[Message(role="user", content="test")],
        )
        await agent.execute(ctx)
        # 检查 system prompt 被传入
        sent_messages = mock.calls[0]["messages"]
        assert sent_messages[0]["role"] == "system"
        assert sent_messages[0]["content"] == "Custom prompt"

    @pytest.mark.asyncio
    async def test_conversation_history_passed(self):
        mock = MockLLMProvider()
        ModelRouter.set_provider(mock)
        agent = ChatAgent()
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[
                Message(role="user", content="first"),
                Message(role="assistant", content="reply"),
                Message(role="user", content="second"),
            ],
        )
        await agent.execute(ctx)
        sent = mock.calls[0]["messages"]
        assert len(sent) == 4  # system + 3 messages
        assert sent[1]["content"] == "first"
        assert sent[2]["content"] == "reply"
        assert sent[3]["content"] == "second"

    @pytest.mark.asyncio
    async def test_execute_handles_error(self):
        mock = MockLLMProvider(error_on="chat")
        ModelRouter.set_provider(mock)
        agent = ChatAgent()
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[Message(role="user", content="test")],
        )
        result = await agent.execute(ctx)
        assert result.success is False
        assert "Mock LLM error" in result.error


class TestExpertPrompts:
    def setup_method(self):
        ModelRouter.reset()

    def teardown_method(self):
        ModelRouter.reset()

    @pytest.mark.asyncio
    async def test_teacher_expert_prompt(self):
        mock = MockLLMProvider()
        ModelRouter.set_provider(mock)
        agent = ChatAgent(expert="teacher")
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[Message(role="user", content="test")],
        )
        await agent.execute(ctx)
        sent = mock.calls[0]["messages"]
        assert "教师" in sent[0]["content"]

    @pytest.mark.asyncio
    async def test_analyst_expert_prompt(self):
        mock = MockLLMProvider()
        ModelRouter.set_provider(mock)
        agent = ChatAgent(expert="analyst")
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[Message(role="user", content="test")],
        )
        await agent.execute(ctx)
        sent = mock.calls[0]["messages"]
        assert "分析师" in sent[0]["content"]


class TestProfileInjection:
    def setup_method(self):
        ModelRouter.reset()

    def teardown_method(self):
        ModelRouter.reset()

    @pytest.mark.asyncio
    async def test_profile_injected_into_system_prompt(self):
        mock = MockLLMProvider()
        ModelRouter.set_provider(mock)
        profile = {
            "interests": ["机器学习", "RAG"],
            "learning_style": "analogy",
            "knowledge_level": {"AI": 75, "ML": 40},
        }
        agent = ChatAgent(profile=profile)
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[Message(role="user", content="test")],
        )
        await agent.execute(ctx)
        sent = mock.calls[0]["messages"]
        system_prompt = sent[0]["content"]
        assert "用户画像" in system_prompt
        assert "机器学习" in system_prompt
        assert "类比型" in system_prompt

    @pytest.mark.asyncio
    async def test_no_profile_no_injection(self):
        mock = MockLLMProvider()
        ModelRouter.set_provider(mock)
        agent = ChatAgent(profile=None)
        ctx = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[Message(role="user", content="test")],
        )
        await agent.execute(ctx)
        sent = mock.calls[0]["messages"]
        assert "用户画像" not in sent[0]["content"]


class TestFormatProfile:
    def test_empty_profile(self):
        assert format_profile({}) == ""
        assert format_profile({"interests": []}) == ""

    def test_full_profile(self):
        profile = {
            "interests": ["ML", "DL"],
            "learning_style": "formula",
            "cognitive_pattern": "top-down",
            "knowledge_level": {"AI": 80},
        }
        result = format_profile(profile)
        assert "用户画像" in result
        assert "ML" in result
        assert "公式型" in result
        assert "自上而下" in result
        assert "AI(80)" in result
