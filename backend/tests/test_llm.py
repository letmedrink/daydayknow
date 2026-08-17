import json

import httpx
import pytest

from app.llm import call_llm_with_config, call_vision_with_config, get_llm_config, stream_llm
from app.storage import FileStore


@pytest.mark.asyncio
async def test_openai_adapter(monkeypatch):
    async def handler(request):
        assert request.url.path.endswith("/chat/completions")
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    result = await call_llm_with_config(
        {"api_key": "test", "base_url": "https://example.test/v1", "model": "model", "api_mode": "openai"},
        [{"role": "user", "content": "hello"}],
    )
    assert result == "ok"


@pytest.mark.asyncio
async def test_anthropic_adapter(monkeypatch):
    async def handler(request):
        payload = json.loads(request.content)
        assert payload["system"] == "system"
        assert request.headers["anthropic-version"] == "2023-06-01"
        return httpx.Response(200, json={"content": [{"type": "text", "text": "ok"}]})

    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    result = await call_llm_with_config(
        {"api_key": "test", "base_url": "https://api.anthropic.test/v1", "model": "claude", "api_mode": "anthropic"},
        [{"role": "system", "content": "system"}, {"role": "user", "content": "hello"}],
    )
    assert result == "ok"


def test_global_provider_precedes_environment(tmp_path):
    store = FileStore(tmp_path)
    store.update_settings(
        llmProviders={"one": {"api_key": "stored", "base_url": "https://stored.test", "model": "m"}},
        activeProviderId="one",
    )
    assert get_llm_config(store)["api_key"] == "stored"


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["openai", "anthropic"])
async def test_vision_adapter_uses_provider_protocol(mode, monkeypatch):
    async def handler(request):
        payload = json.loads(request.content)
        if mode == "anthropic":
            image = payload["messages"][0]["content"][0]
            assert image["source"]["data"] == "aW1hZ2U="
            return httpx.Response(200, json={"content": [{"type": "text", "text": "caption"}]})
        image_url = payload["messages"][0]["content"][1]["image_url"]["url"]
        assert image_url.endswith("aW1hZ2U=")
        return httpx.Response(200, json={"choices": [{"message": {"content": "caption"}}]})

    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    result = await call_vision_with_config(
        {"api_key": "test", "base_url": "https://example.test/v1", "model": "vision", "api_mode": mode},
        "aW1hZ2U=", "image/png", "describe",
    )
    assert result == "caption"
