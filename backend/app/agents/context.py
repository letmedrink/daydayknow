from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Message:
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass
class AgentContext:
    """Agent 共享上下文，在编排中传递。"""

    conversation_id: str
    user_id: str
    messages: List[Message] = field(default_factory=list)
    intermediate_results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
