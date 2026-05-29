from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from .context import AgentContext
from ..utils.logger import create_module_logger


@dataclass
class AgentResult:
    success: bool
    data: Any = None
    error: str | None = None


class BaseAgent(ABC):
    """Agent 抽象基类。所有 Agent 实现 execute 方法。"""

    name: str = "base"
    description: str = ""

    def __init__(self):
        self.log = create_module_logger(f"agent.{self.name}")

    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        ...
