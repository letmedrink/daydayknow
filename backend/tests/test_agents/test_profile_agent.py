import json
import pytest

from app.agents.profile_agent import ProfileAgent
from app.agents.context import AgentContext, Message
from app.agents.registry import AgentRegistry
from app.services.llm.mock import MockLLMProvider
from app.services.llm.router import ModelRouter


class TestProfileAgent:
    def setup_method(self):
        ModelRouter.reset()

    def teardown_method(self):
        ModelRouter.reset()

    @pytest.mark.asyncio
    async def test_returns_profile_data(self):
        profile_data = {
            "knowledge_level": {"AI": 60},
            "interests": ["机器学习"],
            "learning_style": "analogy",
            "cognitive_pattern": "top-down",
            "depth_preference": "moderate",
            "communication_preference": "concise",
            "learning_goals": ["掌握ML基础"],
            "knowledge_gaps": [],
            "misconceptions": [],
        }
        mock = MockLLMProvider()
        mock.default_response = json.dumps(profile_data)
        ModelRouter.set_provider(mock)

        agent = ProfileAgent()
        context = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[
                Message(role="user", content="什么是机器学习"),
                Message(role="assistant", content="ML是AI的一个分支..."),
            ],
        )
        result = await agent.execute(context)
        assert result.success
        assert result.data["learning_style"] == "analogy"
        assert result.data["knowledge_level"]["AI"] == 60

    @pytest.mark.asyncio
    async def test_handles_malformed_json(self):
        mock = MockLLMProvider()
        mock.default_response = "not json"
        ModelRouter.set_provider(mock)

        agent = ProfileAgent()
        context = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[Message(role="user", content="hello")],
        )
        result = await agent.execute(context)
        # Mock provider gracefully falls back to default JSON response
        assert result.success is True
        assert isinstance(result.data, dict)

    @pytest.mark.asyncio
    async def test_handles_non_dict_response(self):
        mock = MockLLMProvider()
        mock.default_response = json.dumps(["a", "list"])
        ModelRouter.set_provider(mock)

        agent = ProfileAgent()
        context = AgentContext(
            conversation_id="c1",
            user_id="u1",
            messages=[Message(role="user", content="hello")],
        )
        result = await agent.execute(context)
        assert not result.success
