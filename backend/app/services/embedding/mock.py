import hashlib
from typing import List

from .base import EmbeddingProvider


class MockEmbeddingProvider(EmbeddingProvider):
    """测试用 Mock Embedding 供应商。基于文本哈希生成确定性向量。"""

    def __init__(self, dimensions: int = 768):
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, text: str) -> List[float]:
        return self._text_to_vec(text)

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self._text_to_vec(t) for t in texts]

    def _text_to_vec(self, text: str) -> List[float]:
        """从文本哈希生成确定性伪向量。相同文本 → 相同向量。"""
        h = hashlib.sha256(text.encode()).digest()
        values = []
        for i in range(self._dimensions):
            byte_idx = i % len(h)
            values.append((h[byte_idx] / 255.0) * 2 - 1)  # 映射到 [-1, 1]
        return values
