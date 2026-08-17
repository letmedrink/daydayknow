"""LLM provider adapters for OpenAI-compatible and Anthropic protocols."""

import json
from typing import AsyncIterator, Optional

import httpx

from .config import settings
from .storage import FileStore


class LLMError(RuntimeError):
    pass


def get_active_provider(global_store: FileStore) -> Optional[dict]:
    stored = global_store.get_settings()
    providers = stored.get("llmProviders", {})
    active_id = stored.get("activeProviderId", "")
    if active_id and active_id in providers:
        return providers[active_id]
    return next((provider for provider in providers.values() if provider.get("api_key")), None)


def get_llm_config(global_store: FileStore) -> dict:
    provider = get_active_provider(global_store)
    if provider and provider.get("api_key"):
        return {
            "base_url": provider.get("base_url") or "https://api.openai.com/v1",
            "api_key": provider["api_key"],
            "model": provider.get("model") or "gpt-4o-mini",
            "max_tokens": provider.get("max_tokens", 4096),
            "temperature": provider.get("temperature", 0.7),
            "api_mode": provider.get("api_mode", "openai"),
            "context_window": provider.get("context_window", 0),
        }
    return {
        "base_url": settings.LLM_BASE_URL or "https://api.openai.com/v1",
        "api_key": settings.LLM_API_KEY or "",
        "model": settings.LLM_MODEL or "gpt-4o-mini",
        "max_tokens": settings.LLM_MAX_TOKENS,
        "temperature": settings.LLM_TEMPERATURE,
        "api_mode": "openai",
        "context_window": 0,
    }


def _provider_error(provider: str, response: httpx.Response) -> LLMError:
    request_id = response.headers.get("request-id") or response.headers.get("x-request-id")
    suffix = f" (request_id={request_id})" if request_id else ""
    return LLMError(f"{provider} API 调用失败: HTTP {response.status_code}{suffix}")


def _anthropic_url(base_url: str) -> str:
    url = base_url.rstrip("/")
    return url if url.endswith("/messages") else f"{url}/messages"


async def call_llm_with_config(
    config: dict,
    messages: list[dict],
    *,
    timeout: float = 120,
    max_tokens: Optional[int] = None,
) -> str:
    if not config.get("api_key"):
        raise LLMError("LLM API Key 未配置，请在设置页面配置")
    mode = config.get("api_mode", "openai")
    async with httpx.AsyncClient(timeout=timeout) as client:
        if mode == "anthropic":
            system_messages = [m["content"] for m in messages if m["role"] == "system"]
            body = {
                "model": config.get("model") or "claude-sonnet-4-20250514",
                "system": "\n\n".join(system_messages),
                "messages": [m for m in messages if m["role"] != "system"],
                "max_tokens": max_tokens or config.get("max_tokens", 4096),
                "temperature": config.get("temperature", 0.7),
            }
            response = await client.post(
                _anthropic_url(config.get("base_url") or "https://api.anthropic.com/v1"),
                headers={"x-api-key": config["api_key"], "anthropic-version": "2023-06-01"},
                json=body,
            )
            if response.status_code != 200:
                raise _provider_error("Anthropic", response)
            return "".join(block.get("text", "") for block in response.json().get("content", []) if block.get("type") == "text")

        response = await client.post(
            f"{(config.get('base_url') or 'https://api.openai.com/v1').rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {config['api_key']}"},
            json={
                "model": config.get("model") or "gpt-4o-mini",
                "messages": messages,
                "max_tokens": max_tokens or config.get("max_tokens", 4096),
                "temperature": config.get("temperature", 0.7),
            },
        )
        if response.status_code != 200:
            raise _provider_error("OpenAI", response)
        return response.json()["choices"][0]["message"]["content"]


async def call_llm(global_store: FileStore, system_prompt: str, user_content: str) -> str:
    return await call_llm_with_config(
        get_llm_config(global_store),
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}],
    )


async def call_vision_with_config(
    config: dict,
    image_data: str,
    media_type: str,
    prompt: str,
    *,
    timeout: float = 30,
) -> str:
    """Call the active provider's vision protocol with a base64 image."""
    if not config.get("api_key"):
        raise LLMError("LLM API Key 未配置，请在设置页面配置")
    async with httpx.AsyncClient(timeout=timeout) as client:
        if config.get("api_mode") == "anthropic":
            response = await client.post(
                _anthropic_url(config.get("base_url") or "https://api.anthropic.com/v1"),
                headers={"x-api-key": config["api_key"], "anthropic-version": "2023-06-01"},
                json={
                    "model": config["model"],
                    "max_tokens": 200,
                    "messages": [{"role": "user", "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}},
                        {"type": "text", "text": prompt},
                    ]}],
                },
            )
            if response.status_code != 200:
                raise _provider_error("Anthropic", response)
            return "".join(
                block.get("text", "") for block in response.json().get("content", [])
                if block.get("type") == "text"
            ).strip()
        response = await client.post(
            f"{config['base_url'].rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {config['api_key']}"},
            json={
                "model": config["model"],
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{image_data}"}},
                ]}],
                "max_tokens": 200,
            },
        )
        if response.status_code != 200:
            raise _provider_error("OpenAI", response)
        return response.json()["choices"][0]["message"]["content"].strip()


async def stream_llm(global_store: FileStore, messages: list[dict]) -> AsyncIterator[dict]:
    config = get_llm_config(global_store)
    if not config.get("api_key"):
        raise LLMError("LLM API Key 未配置，请在设置页面配置")
    mode = config.get("api_mode", "openai")
    if mode == "anthropic":
        async for event in _stream_anthropic(config, messages):
            yield event
    else:
        async for event in _stream_openai(config, messages):
            yield event


async def _stream_openai(config: dict, messages: list[dict]) -> AsyncIterator[dict]:
    url = f"{config['base_url'].rstrip('/')}/chat/completions"
    body = {
        "model": config["model"], "messages": messages,
        "max_tokens": config["max_tokens"], "temperature": config["temperature"], "stream": True,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream("POST", url, headers={"Authorization": f"Bearer {config['api_key']}"}, json=body) as response:
            if response.status_code != 200:
                await response.aread()
                raise _provider_error("OpenAI", response)
            async for line in response.aiter_lines():
                if not line.startswith("data: ") or line[6:].strip() == "[DONE]":
                    continue
                try:
                    delta = json.loads(line[6:])["choices"][0].get("delta", {})
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
                reasoning = delta.get("reasoning_content") or delta.get("reasoning")
                if reasoning:
                    yield {"type": "reasoning", "content": reasoning}
                elif delta.get("content"):
                    yield {"type": "content", "content": delta["content"]}


async def _stream_anthropic(config: dict, messages: list[dict]) -> AsyncIterator[dict]:
    system_messages = [m["content"] for m in messages if m["role"] == "system"]
    body = {
        "model": config["model"], "system": "\n\n".join(system_messages),
        "messages": [m for m in messages if m["role"] != "system"],
        "max_tokens": config["max_tokens"], "temperature": config["temperature"], "stream": True,
    }
    headers = {"x-api-key": config["api_key"], "anthropic-version": "2023-06-01"}
    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream("POST", _anthropic_url(config["base_url"]), headers=headers, json=body) as response:
            if response.status_code != 200:
                await response.aread()
                raise _provider_error("Anthropic", response)
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                try:
                    event = json.loads(line[6:])
                except json.JSONDecodeError:
                    continue
                if event.get("type") == "content_block_delta":
                    delta = event.get("delta", {})
                    if delta.get("type") == "thinking_delta" and delta.get("thinking"):
                        yield {"type": "reasoning", "content": delta["thinking"]}
                    elif delta.get("text"):
                        yield {"type": "content", "content": delta["text"]}
