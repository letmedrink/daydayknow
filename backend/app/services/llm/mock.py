import json
from typing import AsyncIterator, Dict, List, Optional, Any

from .base import LLMProvider


class MockLLMProvider(LLMProvider):
    """用于测试的 Mock 供应商。支持自定义响应、调用记录、错误模拟。"""

    DEFAULT_JSON_RESPONSE = {
        "nodes": [],
        "edges": [],
        "conflicts": [],
        "has_conflict": False,
        "intent": "chat",
        "expert": "generalist",
        "depth": "quick",
    }

    def __init__(
        self,
        responses: Optional[Dict[str, str]] = None,
        json_responses: Optional[Dict[str, Dict]] = None,
        error_on: Optional[str] = None,
    ):
        self.responses = responses or {}
        self.json_responses = json_responses or {}
        self.error_on = error_on
        self.calls: List[Dict[str, Any]] = []
        self.default_response = "Mock response"

    def _get_last_user_message(self, messages: List[Dict[str, str]]) -> str:
        user_msgs = [m["content"] for m in messages if m["role"] == "user"]
        return user_msgs[-1] if user_msgs else ""

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs,
    ) -> str:
        self.calls.append({"method": "chat", "messages": messages, "temperature": temperature})
        if self.error_on == "chat":
            raise RuntimeError("Mock LLM error on chat")
        last_msg = self._get_last_user_message(messages)
        return self.responses.get(last_msg, self.default_response)

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs,
    ) -> AsyncIterator[str]:
        self.calls.append({"method": "chat_stream", "messages": messages})
        if self.error_on == "chat_stream":
            raise RuntimeError("Mock LLM error on chat_stream")
        response = await self.chat(messages, temperature=temperature, max_tokens=max_tokens)
        # 从 calls 中移除 chat 调用（chat_stream 内部调用 chat 会产生额外记录）
        for i in range(len(self.calls) - 1, -1, -1):
            if self.calls[i]["method"] == "chat":
                self.calls.pop(i)
                break
        # 模拟流式：每 20 字符产出一块
        for i in range(0, len(response), 20):
            yield response[i : i + 20]

    async def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        **kwargs,
    ) -> Dict[str, Any]:
        self.calls.append({"method": "chat_json", "messages": messages})
        if self.error_on == "chat_json":
            raise RuntimeError("Mock LLM error on chat_json")
        last_msg = self._get_last_user_message(messages)
        if last_msg in self.json_responses:
            return self.json_responses[last_msg]
        response = self.responses.get(last_msg, self.default_response)
        try:
            return json.loads(response)
        except (json.JSONDecodeError, ValueError):
            return self.DEFAULT_JSON_RESPONSE.copy()
