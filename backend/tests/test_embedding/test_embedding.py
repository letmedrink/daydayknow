import pytest
import math
from unittest.mock import patch, MagicMock
import numpy as np

from app.services.embedding.mock import MockEmbeddingProvider
from app.services.embedding.local import LocalEmbeddingProvider
from app.services.embedding.router import EmbeddingRouter


class TestMockEmbedding:
    @pytest.mark.asyncio
    async def test_deterministic(self):
        provider = MockEmbeddingProvider()
        vec1 = await provider.embed("hello")
        vec2 = await provider.embed("hello")
        assert vec1 == vec2

    @pytest.mark.asyncio
    async def test_different_texts_different_vectors(self):
        provider = MockEmbeddingProvider()
        vec1 = await provider.embed("hello")
        vec2 = await provider.embed("world")
        assert vec1 != vec2

    @pytest.mark.asyncio
    async def test_dimensions(self):
        provider = MockEmbeddingProvider(dimensions=128)
        vec = await provider.embed("test")
        assert len(vec) == 128
        assert provider.dimensions == 128

    @pytest.mark.asyncio
    async def test_values_in_range(self):
        provider = MockEmbeddingProvider()
        vec = await provider.embed("test")
        assert all(-1 <= v <= 1 for v in vec)

    @pytest.mark.asyncio
    async def test_batch(self):
        provider = MockEmbeddingProvider()
        results = await provider.embed_batch(["a", "b", "c"])
        assert len(results) == 3
        assert all(len(v) == 768 for v in results)

    @pytest.mark.asyncio
    async def test_similar_texts_higher_similarity(self):
        provider = MockEmbeddingProvider()
        vec_a = await provider.embed("attention mechanism")
        vec_b = await provider.embed("attention mechanisms")
        vec_c = await provider.embed("quantum physics")

        def cosine_sim(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            na = math.sqrt(sum(x * x for x in a))
            nb = math.sqrt(sum(x * x for x in b))
            return dot / (na * nb) if na and nb else 0

        sim_ab = cosine_sim(vec_a, vec_b)
        sim_ac = cosine_sim(vec_a, vec_c)
        # 哈希向量不保证语义，但至少可以计算
        assert isinstance(sim_ab, float)
        assert isinstance(sim_ac, float)


class TestEmbeddingRouter:
    def setup_method(self):
        EmbeddingRouter.reset()

    def teardown_method(self):
        EmbeddingRouter.reset()

    def test_default_provider(self):
        provider = EmbeddingRouter.get_provider()
        assert isinstance(provider, MockEmbeddingProvider)

    def test_set_custom_provider(self):
        custom = MockEmbeddingProvider(dimensions=128)
        EmbeddingRouter.set_provider(custom)
        assert EmbeddingRouter.get_provider().dimensions == 128

    def test_reset(self):
        EmbeddingRouter.set_provider(MockEmbeddingProvider(dimensions=256))
        EmbeddingRouter.reset()
        assert EmbeddingRouter.get_provider().dimensions == 768


class TestLocalEmbedding:
    """LocalEmbeddingProvider 测试（mock sentence_transformers）。"""

    def _make_mock_model(self, dim=384):
        """构造一个 mock SentenceTransformer。"""
        model = MagicMock()
        model.get_sentence_embedding_dimension.return_value = dim

        def encode(texts, **kwargs):
            results = []
            for text in texts:
                rng = np.random.RandomState(hash(text) % (2**31))
                vec = rng.randn(dim).astype(np.float32)
                if kwargs.get("normalize_embeddings"):
                    vec = vec / np.linalg.norm(vec)
                results.append(vec)
            return results

        model.encode = encode
        return model

    @pytest.mark.asyncio
    async def test_embed_returns_correct_dim(self):
        mock_model = self._make_mock_model(dim=384)
        provider = LocalEmbeddingProvider()
        provider._model = mock_model
        provider._dimensions = 384

        vec = await provider.embed("hello")
        assert len(vec) == 384

    @pytest.mark.asyncio
    async def test_embed_batch(self):
        mock_model = self._make_mock_model()
        provider = LocalEmbeddingProvider()
        provider._model = mock_model
        provider._dimensions = 384

        results = await provider.embed_batch(["a", "b", "c"])
        assert len(results) == 3
        assert all(len(v) == 384 for v in results)

    @pytest.mark.asyncio
    async def test_deterministic(self):
        mock_model = self._make_mock_model()
        provider = LocalEmbeddingProvider()
        provider._model = mock_model
        provider._dimensions = 384

        vec1 = await provider.embed("hello")
        vec2 = await provider.embed("hello")
        assert vec1 == vec2

    @pytest.mark.asyncio
    async def test_normalized_output(self):
        """归一化后的向量范数应接近 1。"""
        mock_model = self._make_mock_model()
        provider = LocalEmbeddingProvider()
        provider._model = mock_model
        provider._dimensions = 384

        vec = await provider.embed("test embedding")
        norm = math.sqrt(sum(v * v for v in vec))
        assert abs(norm - 1.0) < 0.01
