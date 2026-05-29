from typing import AsyncIterator

from .base import BaseAgent, AgentResult
from .context import AgentContext
from .registry import AgentRegistry
from ..services.llm.router import ModelRouter

# 简单 token 估算：1 中文字符 ≈ 1.5 token，1 英文单词 ≈ 1.3 token
# 保守估计：每字符 2 token
CHARS_PER_TOKEN = 0.5

EXPERT_PROMPTS = {
    "generalist": "你是一个知识渊博的学习助手。用简洁清晰的语言回答用户的问题。如果用户提到你不熟悉的概念，请诚实说明。",
    "teacher": "你是一位循循善诱的教师。擅长用类比和例子讲解概念，引导用户逐步理解。遇到复杂概念时，先给出直觉类比，再深入细节。",
    "analyst": "你是一位严谨的分析师。回答要有清晰的逻辑框架，善用数据和事实支撑观点。给出结构化的分析，必要时使用表格和列表。",
}

DEPTH_TOKENS = {
    "quick": 3000,
    "deep": 8000,
}


def estimate_tokens(text: str) -> int:
    return int(len(text) / CHARS_PER_TOKEN)


def truncate_messages(
    messages: list[dict],
    max_tokens: int = 6000,
    max_messages: int = 20,
) -> list[dict]:
    """截断消息列表，保留系统消息 + 最近的消息，控制在 token 预算内。"""
    if not messages:
        return messages

    system_msg = None
    chat_msgs = messages
    if messages[0]["role"] == "system":
        system_msg = messages[0]
        chat_msgs = messages[1:]

    # 先按 max_messages 限制
    if len(chat_msgs) > max_messages:
        chat_msgs = chat_msgs[-max_messages:]

    # 再按 token 预算限制（从后往前保留）
    token_budget = max_tokens - (estimate_tokens(system_msg["content"]) if system_msg else 0)
    kept = []
    used_tokens = 0
    for msg in reversed(chat_msgs):
        msg_tokens = estimate_tokens(msg["content"])
        if used_tokens + msg_tokens > token_budget and kept:
            break
        kept.append(msg)
        used_tokens += msg_tokens
    kept.reverse()

    result = []
    if system_msg:
        result.append(system_msg)
    result.extend(kept)
    return result


def format_profile(profile: dict) -> str:
    """将画像数据格式化为 system prompt 段落。"""
    lines = []
    if profile.get("interests"):
        lines.append(f"- 兴趣方向: {', '.join(profile['interests'][:5])}")
    if profile.get("learning_style"):
        style_map = {"analogy": "类比型", "formula": "公式型", "case": "案例型", "diagram": "图解型"}
        lines.append(f"- 学习风格: {style_map.get(profile['learning_style'], profile['learning_style'])}")
    if profile.get("cognitive_pattern"):
        cog_map = {"top-down": "自上而下", "bottom-up": "自下而上", "mixed": "混合型"}
        lines.append(f"- 认知模式: {cog_map.get(profile['cognitive_pattern'], profile['cognitive_pattern'])}")
    if profile.get("knowledge_level") and isinstance(profile["knowledge_level"], dict):
        levels = [f"{k}({v})" for k, v in list(profile["knowledge_level"].items())[:3]]
        if levels:
            lines.append(f"- 知识水平: {', '.join(levels)}")
    if not lines:
        return ""
    return "\n\n[用户画像]\n" + "\n".join(lines) + "\n请根据用户画像调整讲解方式。"


@AgentRegistry.register("chat")
class ChatAgent(BaseAgent):
    name = "chat"
    description = "对话 Agent，支持流式输出"

    def __init__(self, system_prompt: str | None = None, expert: str = "generalist",
                 profile: dict | None = None, max_tokens: int = 6000):
        super().__init__()
        base_prompt = system_prompt or EXPERT_PROMPTS.get(expert, EXPERT_PROMPTS["generalist"])
        profile_text = format_profile(profile) if profile else ""
        self.system_prompt = base_prompt + profile_text
        self.max_tokens = max_tokens

    def _build_messages(self, context: AgentContext):
        messages = [{"role": "system", "content": self.system_prompt}]
        for msg in context.messages:
            messages.append({"role": msg.role, "content": msg.content})

        # 从路由结果读取 depth 覆盖 max_tokens
        routing = context.intermediate_results.get("routing", {})
        depth = routing.get("depth", "quick")
        max_tokens = DEPTH_TOKENS.get(depth, self.max_tokens)

        return truncate_messages(messages, max_tokens=max_tokens)

    async def execute(self, context: AgentContext) -> AgentResult:
        messages = self._build_messages(context)
        provider = ModelRouter.get_provider()
        try:
            response = await provider.chat(messages)
            return AgentResult(success=True, data={"response": response})
        except Exception as e:
            self.log.error("Chat failed", e)
            return AgentResult(success=False, error=str(e))

    async def stream(self, context: AgentContext) -> AsyncIterator[str]:
        """流式产出，用于 SSE。不在 BaseAgent 上——只有对话 Agent 需要。"""
        messages = self._build_messages(context)
        provider = ModelRouter.get_provider()
        async for chunk in provider.chat_stream(messages):
            yield chunk
