"""基于 sentence-transformers 的本地 Embedding 供应商。"""
import asyncio
from typing import List
from concurrent.futures import ThreadPoolExecutor

from .base import EmbeddingProvider

_executor = ThreadPoolExecutor(max_workers=1)


class LocalEmbeddingProvider(EmbeddingProvider):
    """使用 sentence-transformers 本地模型生成向量。

    模型在首次调用时懒加载，之后缓存在内存中。
    默认使用 BAAI/bge-small-zh-v1.5（中文优化，128MB）。
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-zh-v1.5",
        dimensions: int = 512,
    ):
        self.model_name = model_name
        self._dimensions = dimensions
        self._model = None

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def _load_model(self):
        """懒加载模型（同步）。"""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            self._dimensions = self._model.get_sentence_embedding_dimension()
        return self._model

    async def embed(self, text: str) -> List[float]:
        results = await self.embed_batch([text])
        return results[0]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            self._encode_sync,
            texts,
        )

    def _encode_sync(self, texts: List[str]) -> List[List[float]]:
        model = self._load_model()
        embeddings = model.encode(texts, normalize_embeddings=True)
        return [emb.tolist() for emb in embeddings]
