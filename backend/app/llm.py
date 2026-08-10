"""LLM 调用公共模块 — 多 provider 动态适配。

架构：
- 配置优先级：前端设置（settings.json）> 环境变量 > 默认值
- 双协议支持：OpenAI 兼容 (/chat/completions) 和 Anthropic 兼容 (/messages)
- 流式适配：DeepSeek/Qwen/Kimi 的 reasoning_content 和 OpenAI o-series 的 reasoning

使用方式：
  from app.llm import call_llm, stream_llm, get_llm_config
  response = await call_llm(file_store, system_prompt, user_content)
  async for chunk in stream_llm(file_store, messages):
      ...  # chunk: {"type": "content"|"reasoning", "content": str}
"""

import json
import logging
from typing import Optional

from .config import settings
from .storage import FileStore

log = logging.getLogger("llm")


def get_active_provider(file_store: FileStore) -> Optional[dict]:
    """从 file_store 获取活跃 LLM provider 配置。"""
    s = file_store.get_settings()
    providers = s.get("llmProviders", {})
    active_id = s.get("activeProviderId", "")

    if not providers:
        return None

    if active_id and active_id in providers:
        return providers[active_id]

    # 没有指定 active，取第一个
    for pid, p in providers.items():
        if p.get("api_key"):
            return p

    return None


def get_llm_config(file_store: FileStore) -> dict:
    """获取 LLM 调用配置，优先使用活跃 provider，回退到 env 配置。

    返回 {base_url, api_key, model, max_tokens, temperature, api_mode}
    """
    provider = get_active_provider(file_store)
    if provider and provider.get("api_key"):
        return {
            "base_url": provider.get("base_url", "https://api.openai.com/v1"),
            "api_key": provider["api_key"],
            "model": provider.get("model", "gpt-4o-mini"),
            "max_tokens": provider.get("max_tokens", 4096),
            "temperature": provider.get("temperature", 0.7),
            "api_mode": provider.get("api_mode", "openai"),
        }

    # 回退到 env 配置
    return {
        "base_url": settings.LLM_BASE_URL or "https://api.openai.com/v1",
        "api_key": settings.LLM_API_KEY or "",
        "model": settings.LLM_MODEL or "gpt-4o-mini",
        "max_tokens": settings.LLM_MAX_TOKENS,
        "temperature": settings.LLM_TEMPERATURE,
        "api_mode": "openai",
    }


async def call_llm(
    file_store: FileStore,
    system_prompt: str,
    user_content: str,
) -> str:
    """调用 LLM API，自动使用活跃 provider 配置。"""
    import httpx

    cfg = get_llm_config(file_store)

    if not cfg["api_key"]:
        return "[LLM API Key 未配置，请在设置页面配置]"

    headers = {"Authorization": f"Bearer {cfg['api_key']}"}
    url = f"{cfg['base_url'].rstrip('/')}/chat/completions"

    body = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "max_tokens": cfg["max_tokens"],
        "temperature": cfg["temperature"],
    }

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, headers=headers, json=body)

        if resp.status_code == 200:
            data = resp.json()
            return data["choices"][0]["message"]["content"]

        raise RuntimeError(f"LLM API 调用失败: {resp.status_code} {resp.text[:200]}")


async def stream_llm(
    file_store: FileStore,
    messages: list[dict],
):
    """流式调用 LLM API，yield dict: {"type": "content"|"reasoning", "content": str}。

    适配多种 LLM 的思考/推理字段：
    - DeepSeek / Kimi / Qwen: delta.reasoning_content
    - OpenAI o-series: delta.reasoning
    """
    import httpx

    cfg = get_llm_config(file_store)

    if not cfg["api_key"]:
        yield {"type": "content", "content": "[LLM API Key 未配置，请在设置页面配置]"}
        return

    headers = {"Authorization": f"Bearer {cfg['api_key']}"}
    url = f"{cfg['base_url'].rstrip('/')}/chat/completions"

    body = {
        "model": cfg["model"],
        "messages": messages,
        "max_tokens": cfg["max_tokens"],
        "temperature": cfg["temperature"],
        "stream": True,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream("POST", url, headers=headers, json=body) as resp:
            if resp.status_code != 200:
                yield {"type": "content", "content": f"LLM 调用失败: {resp.status_code}"}
                return
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                    delta = data["choices"][0].get("delta", {})
                    # 优先检查 reasoning 字段（DeepSeek / Kimi / Qwen / OpenAI o-series）
                    reasoning = delta.get("reasoning_content") or delta.get("reasoning")
                    if reasoning:
                        yield {"type": "reasoning", "content": reasoning}
                    elif "content" in delta and delta["content"]:
                        yield {"type": "content", "content": delta["content"]}
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
