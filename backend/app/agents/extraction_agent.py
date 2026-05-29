from .base import BaseAgent, AgentResult
from .context import AgentContext
from .registry import AgentRegistry
from ..services.llm.router import ModelRouter


EXTRACTION_PROMPT = """你是一个知识提取专家。从对话文本中提取关键概念和它们之间的关系。

输出JSON格式：
{
  "nodes": [
    {"name": "概念名称", "domain": "所属领域", "description": "简短描述", "confidence": 0.85}
  ],
  "edges": [
    {"from": "概念A", "to": "概念B", "relation_type": "is-a", "description": "A是B的一种", "strength": 0.9}
  ]
}

关系类型限制为以下之一：
is-a, part-of, causes, enables, requires, similar-to, applies-to, solves, derived-from

要求：
- 只提取对话中明确讨论的概念（最多5个）
- 关系必须在对话中有依据
- confidence表示提取的置信度（0-1）"""


@AgentRegistry.register("extraction")
class ExtractionAgent(BaseAgent):
    name = "extraction"
    description = "从对话中提取概念和关系"

    async def execute(self, context: AgentContext) -> AgentResult:
        conv_text = "\n".join(f"{m.role}: {m.content}" for m in context.messages)
        messages = [
            {"role": "system", "content": EXTRACTION_PROMPT},
            {"role": "user", "content": f"从以下对话中提取知识：\n\n{conv_text}"},
        ]
        provider = ModelRouter.get_provider()
        try:
            result = await provider.chat_json(messages)
            # 基本校验
            if not isinstance(result, dict) or "nodes" not in result:
                return AgentResult(
                    success=False, error="Extraction result missing 'nodes' field"
                )
            return AgentResult(success=True, data=result)
        except Exception as e:
            self.log.error("Extraction failed", e)
            return AgentResult(success=False, error=str(e))
