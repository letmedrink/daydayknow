import pytest

from app.services.llm.router import ModelRouter
from app.services.llm.mock import MockLLMProvider
from app.services.llm.base import LLMProvider


class TestModelRouter:
    def setup_method(self):
        ModelRouter.reset()

    def teardown_method(self):
        ModelRouter.reset()

    def test_get_provider_returns_provider(self, monkeypatch):
        monkeypatch.setattr("app.services.llm.router.settings.MOCK_MODE", True)
        provider = ModelRouter.get_provider()
        assert isinstance(provider, LLMProvider)

    def test_get_provider_returns_mock_in_mock_mode(self, monkeypatch):
        monkeypatch.setattr("app.services.llm.router.settings.MOCK_MODE", True)
        provider = ModelRouter.get_provider()
        assert isinstance(provider, MockLLMProvider)

    def test_set_provider_override(self):
        custom = MockLLMProvider(responses={"test": "custom"})
        ModelRouter.set_provider(custom)
        assert ModelRouter.get_provider() is custom

    def test_reset_clears_provider(self, monkeypatch):
        monkeypatch.setattr("app.services.llm.router.settings.MOCK_MODE", True)
        ModelRouter.get_provider()
        ModelRouter.reset()
        provider = ModelRouter.get_provider()
        assert isinstance(provider, LLMProvider)

    def test_unknown_provider_raises(self, monkeypatch):
        monkeypatch.setattr("app.services.llm.router.settings.MOCK_MODE", False)
        monkeypatch.setattr("app.services.llm.router.settings.LLM_PROVIDER", "unknown")
        monkeypatch.setattr("app.services.llm.router.settings.LLM_API_KEY", "key")
        monkeypatch.setattr("app.services.llm.router.settings.LLM_MODEL", "")
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            ModelRouter.get_provider()

    @pytest.mark.asyncio
    async def test_mock_provider_works_through_router(self, monkeypatch):
        monkeypatch.setattr("app.services.llm.router.settings.MOCK_MODE", True)
        provider = ModelRouter.get_provider()
        result = await provider.chat([{"role": "user", "content": "hi"}])
        assert result == "Mock response"
