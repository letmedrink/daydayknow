from .base import EmbeddingProvider
from .mock import MockEmbeddingProvider


class EmbeddingRouter:
    """Embedding 供应商路由。全局单例。"""

    _provider: EmbeddingProvider | None = None

    @classmethod
    def get_provider(cls) -> EmbeddingProvider:
        if cls._provider is None:
            cls._provider = MockEmbeddingProvider()
        return cls._provider

    @classmethod
    def set_provider(cls, provider: EmbeddingProvider):
        cls._provider = provider

    @classmethod
    def reset(cls):
        cls._provider = None
