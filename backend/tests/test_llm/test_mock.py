import json
import pytest

from app.services.llm.mock import MockLLMProvider


@pytest.fixture
def provider():
    return MockLLMProvider()


@pytest.fixture
def custom_provider():
    return MockLLMProvider(
        responses={"hello": "Hi there!"},
        json_responses={"extract": {"nodes": [{"name": "test"}], "edges": []}},
    )


class TestMockChat:
    @pytest.mark.asyncio
    async def test_default_response(self, provider):
        result = await provider.chat([{"role": "user", "content": "anything"}])
        assert result == "Mock response"

    @pytest.mark.asyncio
    async def test_custom_response(self, custom_provider):
        result = await custom_provider.chat([{"role": "user", "content": "hello"}])
        assert result == "Hi there!"

    @pytest.mark.asyncio
    async def test_records_calls(self, provider):
        await provider.chat([{"role": "user", "content": "test"}], temperature=0.5)
        assert len(provider.calls) == 1
        assert provider.calls[0]["method"] == "chat"
        assert provider.calls[0]["temperature"] == 0.5

    @pytest.mark.asyncio
    async def test_error_simulation(self):
        provider = MockLLMProvider(error_on="chat")
        with pytest.raises(RuntimeError, match="Mock LLM error on chat"):
            await provider.chat([{"role": "user", "content": "test"}])


class TestMockStream:
    @pytest.mark.asyncio
    async def test_stream_yields_chunks(self, provider):
        chunks = []
        async for chunk in provider.chat_stream([{"role": "user", "content": "anything"}]):
            chunks.append(chunk)
        full = "".join(chunks)
        assert full == "Mock response"

    @pytest.mark.asyncio
    async def test_stream_custom_response(self, custom_provider):
        chunks = []
        async for chunk in custom_provider.chat_stream([{"role": "user", "content": "hello"}]):
            chunks.append(chunk)
        assert "".join(chunks) == "Hi there!"

    @pytest.mark.asyncio
    async def test_stream_chunk_size(self):
        provider = MockLLMProvider(responses={"x": "a" * 50})
        chunks = []
        async for chunk in provider.chat_stream([{"role": "user", "content": "x"}]):
            chunks.append(chunk)
        assert len(chunks) == 3  # 50 chars / 20 per chunk = 3
        assert chunks[0] == "a" * 20
        assert chunks[1] == "a" * 20
        assert chunks[2] == "a" * 10


class TestMockJson:
    @pytest.mark.asyncio
    async def test_json_from_json_responses(self, custom_provider):
        result = await custom_provider.chat_json([{"role": "user", "content": "extract"}])
        assert result == {"nodes": [{"name": "test"}], "edges": []}

    @pytest.mark.asyncio
    async def test_json_from_response_string(self):
        data = {"key": "value"}
        provider = MockLLMProvider(responses={"q": json.dumps(data)})
        result = await provider.chat_json([{"role": "user", "content": "q"}])
        assert result == data

    @pytest.mark.asyncio
    async def test_json_invalid_returns_default(self, provider):
        result = await provider.chat_json([{"role": "user", "content": "anything"}])
        assert isinstance(result, dict)
        assert "nodes" in result
