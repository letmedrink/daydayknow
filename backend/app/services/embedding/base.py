from abc import ABC, abstractmethod
from typing import List


class EmbeddingProvider(ABC):
    """Embedding 供应商抽象基类。"""

    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """将文本转换为向量。"""
        ...

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量将文本转换为向量。"""
        ...

    @property
    def dimensions(self) -> int:
        """向量维度。"""
        return 768
