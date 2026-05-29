import json
from typing import Any, AsyncIterator, Dict, List

import anthropic

from .base import LLMProvider


class AnthropicProvider(LLMProvider):
    """Anthropic Claude 供应商。system 消息与 messages 分离。"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def _split_messages(self, messages: List[Dict[str, str]]):
        system = next((m["content"] for m in messages if m["role"] == "system"), None)
        msgs = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
            if m["role"] != "system"
        ]
        return system, msgs

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs,
    ) -> str:
        system, msgs = self._split_messages(messages)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=msgs,
        )
        return response.content[0].text

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs,
    ) -> AsyncIterator[str]:
        system, msgs = self._split_messages(messages)
        with self.client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=msgs,
        ) as stream:
            for text in stream.text_stream:
                yield text

    async def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        **kwargs,
    ) -> Dict[str, Any]:
        # Anthropic 不支持 response_format，通过 prompt 要求 JSON
        json_messages = list(messages)
        if json_messages and json_messages[-1]["role"] == "user":
            json_messages[-1] = {
                "role": "user",
                "content": json_messages[-1]["content"]
                + "\n\n请仅返回合法的 JSON，不要包含 markdown 代码块。",
            }
        response_text = await self.chat(json_messages, temperature=temperature, **kwargs)
        # 清理可能的 markdown 包裹
        text = response_text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
