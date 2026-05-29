from typing import Dict, Type

from .base import BaseAgent


class AgentRegistry:
    """Agent 注册中心。通过装饰器注册，工厂方法创建。"""

    _agents: Dict[str, Type[BaseAgent]] = {}

    @classmethod
    def register(cls, name: str):
        def decorator(agent_cls: Type[BaseAgent]):
            cls._agents[name] = agent_cls
            return agent_cls

        return decorator

    @classmethod
    def get(cls, name: str) -> Type[BaseAgent] | None:
        return cls._agents.get(name)

    @classmethod
    def create(cls, name: str, **kwargs) -> BaseAgent:
        agent_cls = cls._agents.get(name)
        if not agent_cls:
            raise ValueError(f"Agent '{name}' not registered")
        return agent_cls(**kwargs)

    @classmethod
    def list_agents(cls) -> list:
        return list(cls._agents.keys())

    @classmethod
    def reset(cls) -> None:
        cls._agents.clear()
