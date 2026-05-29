from ..services.llm.router import ModelRouter
from .base import BaseAgent, AgentResult
from .context import AgentContext
from .registry import AgentRegistry

PROFILE_PROMPT = """你是一个学习行为分析专家。根据用户与AI的对话记录，分析用户的学习特征并输出JSON。

输出格式（严格JSON）：
{
  "knowledge_level": {"领域名": 0-100的掌握度},
  "knowledge_gaps": ["用户暴露但未深入的概念"],
  "interests": ["用户关注的主题"],
  "learning_style": "analogy" | "formula" | "case" | "diagram",
  "cognitive_pattern": "top-down" | "bottom-up" | "mixed",
  "depth_preference": "shallow" | "moderate" | "deep",
  "communication_preference": "concise" | "detailed" | "code-first",
  "learning_goals": ["推断的学习目标"],
  "misconceptions": ["用户表现出的常见误解"]
}

规则：
- 只从对话内容推断，不要编造
- 如果某个维度无法判断，返回null或空数组
- knowledge_level 根据用户提问质量判断（问基础问题=低分，问高级问题=高分）
- learning_style: 用户喜欢类比解释→analogy，喜欢公式→formula，喜欢案例→case，喜欢图解→diagram
- depth_preference: 用户追问多→deep，用户说"简单说说"→shallow
"""


@AgentRegistry.register("profile")
class ProfileAgent(BaseAgent):
    name = "profile"
    description = "从对话中分析用户学习画像"

    async def execute(self, context: AgentContext) -> AgentResult:
        conversation_text = "\n".join(
            f"{m.role}: {m.content}" for m in context.messages
        )

        messages = [
            {"role": "system", "content": PROFILE_PROMPT},
            {"role": "user", "content": f"从以下对话中分析用户画像：\n\n{conversation_text}"},
        ]

        try:
            provider = ModelRouter.get_provider()
            result = await provider.chat_json(messages)
            if not isinstance(result, dict):
                return AgentResult(success=False, error="Profile result is not a dict")
            return AgentResult(success=True, data=result)
        except Exception as e:
            return AgentResult(success=False, error=str(e))
