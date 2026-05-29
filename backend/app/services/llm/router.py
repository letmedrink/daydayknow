from ...config import settings
from .base import LLMProvider
from .mock import MockLLMProvider


class ModelRouter:
    """LLM 供应商路由器。根据配置创建对应供应商实例。"""

    _provider: LLMProvider | None = None

    @classmethod
    def get_provider(cls) -> LLMProvider:
        if cls._provider is None:
            cls._provider = cls._create_provider()
        return cls._provider

    @classmethod
    def set_provider(cls, provider: LLMProvider) -> None:
        """覆盖供应商（用于测试）。"""
        cls._provider = provider

    @classmethod
    def reset(cls) -> None:
        """重置供应商（用于测试清理）。"""
        cls._provider = None

    @classmethod
    def _create_provider(cls) -> LLMProvider:
        if settings.MOCK_MODE:
            return MockLLMProvider()

        provider_name = settings.LLM_PROVIDER
        api_key = settings.LLM_API_KEY
        model = settings.LLM_MODEL or None

        if provider_name == "deepseek":
            from .deepseek import DeepSeekProvider

            return DeepSeekProvider(api_key=api_key, model=model or "deepseek-chat")
        elif provider_name == "openai":
            from .openai_provider import OpenAIProvider

            return OpenAIProvider(api_key=api_key, model=model or "gpt-4o-mini")
        elif provider_name == "claude":
            from .anthropic_provider import AnthropicProvider

            return AnthropicProvider(
                api_key=api_key, model=model or "claude-sonnet-4-20250514"
            )
        else:
            raise ValueError(f"Unknown LLM provider: {provider_name}")
