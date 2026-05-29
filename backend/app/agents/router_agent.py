from .base import BaseAgent, AgentResult
from .context import AgentContext
from .registry import AgentRegistry
from ..services.llm.router import ModelRouter


ROUTER_PROMPT = """你是对话路由器。分析用户最新的消息，返回JSON：

{
  "intent": "chat" | "explain" | "quiz",
  "expert": "generalist" | "teacher" | "analyst",
  "depth": "quick" | "deep"
}

分类标准：
- intent: chat=闲聊/简单问答, explain=需要详细解释, quiz=用户想测试/练习
- expert: generalist=通才助手, teacher=善用类比教学, analyst=严谨数据驱动
- depth: quick=简短回答, deep=需要深入展开

只返回JSON，不要其他内容。"""


@AgentRegistry.register("router")
class RouterAgent(BaseAgent):
    name = "router"
    description = "意图分类 + 专家角色匹配"

    async def execute(self, context: AgentContext) -> AgentResult:
        # 无历史消息时使用默认路由
        if not context.messages:
            return AgentResult(success=True, data={
                "intent": "chat",
                "expert": "generalist",
                "depth": "quick",
            })

        # 只取最后 3 条消息作为路由依据
        recent = context.messages[-3:]
        conv_text = "\n".join(f"{m.role}: {m.content}" for m in recent)

        messages = [
            {"role": "system", "content": ROUTER_PROMPT},
            {"role": "user", "content": f"路由以下对话：\n\n{conv_text}"},
        ]

        provider = ModelRouter.get_provider()
        try:
            result = await provider.chat_json(messages)
            if not isinstance(result, dict) or "intent" not in result:
                # 兜底默认值
                return AgentResult(success=True, data={
                    "intent": "chat",
                    "expert": "generalist",
                    "depth": "quick",
                })
            # 确保三个字段都有值
            result.setdefault("intent", "chat")
            result.setdefault("expert", "generalist")
            result.setdefault("depth", "quick")
            return AgentResult(success=True, data=result)
        except Exception as e:
            self.log.warn("Router failed, using defaults", e)
            return AgentResult(success=True, data={
                "intent": "chat",
                "expert": "generalist",
                "depth": "quick",
            })
