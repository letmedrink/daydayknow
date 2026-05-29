import pytest

from app.agents.registry import AgentRegistry
from app.agents.base import BaseAgent, AgentResult
from app.agents.context import AgentContext


class DummyAgent(BaseAgent):
    name = "dummy"
    description = "Test agent"

    async def execute(self, context: AgentContext) -> AgentResult:
        return AgentResult(success=True, data="ok")


class TestAgentRegistry:
    def setup_method(self):
        AgentRegistry.reset()

    def teardown_method(self):
        AgentRegistry.reset()

    def test_register_decorator(self):
        AgentRegistry.register("dummy")(DummyAgent)
        assert AgentRegistry.get("dummy") is DummyAgent

    def test_create_instantiates_agent(self):
        AgentRegistry.register("dummy")(DummyAgent)
        agent = AgentRegistry.create("dummy")
        assert isinstance(agent, DummyAgent)

    def test_get_unknown_returns_none(self):
        assert AgentRegistry.get("nonexistent") is None

    def test_create_unknown_raises(self):
        with pytest.raises(ValueError, match="Agent 'nonexistent' not registered"):
            AgentRegistry.create("nonexistent")

    def test_list_agents(self):
        AgentRegistry.register("a")(DummyAgent)
        AgentRegistry.register("b")(DummyAgent)
        assert sorted(AgentRegistry.list_agents()) == ["a", "b"]

    def test_reset_clears(self):
        AgentRegistry.register("dummy")(DummyAgent)
        AgentRegistry.reset()
        assert AgentRegistry.list_agents() == []

    @pytest.mark.asyncio
    async def test_created_agent_executes(self):
        AgentRegistry.register("dummy")(DummyAgent)
        agent = AgentRegistry.create("dummy")
        ctx = AgentContext(conversation_id="c1", user_id="u1")
        result = await agent.execute(ctx)
        assert result.success is True
        assert result.data == "ok"
