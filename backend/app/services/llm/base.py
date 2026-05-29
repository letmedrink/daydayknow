from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Dict, Any


class LLMProvider(ABC):
    """LLM 供应商抽象基类。所有供应商实现此接口。"""

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs,
    ) -> str:
        """非流式对话，返回完整文本。"""
        ...

    @abstractmethod
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs,
    ) -> AsyncIterator[str]:
        """流式对话，逐块产出文本。"""
        ...
        yield ""  # pragma: no cover — 使函数体成为 async generator

    @abstractmethod
    async def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        **kwargs,
    ) -> Dict[str, Any]:
        """JSON 模式对话，返回解析后的字典。"""
        ...
