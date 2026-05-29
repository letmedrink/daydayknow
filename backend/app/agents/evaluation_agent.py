from .base import BaseAgent, AgentResult
from .context import AgentContext
from .registry import AgentRegistry
from ..services.llm.router import ModelRouter


EVAL_PROMPT = """你是一个知识提取质量评估专家。

给定对话内容和提取结果，评估提取质量并给出改进建议。

输出JSON格式：
{
  "score": 0-100的整数,
  "issues": [
    {"type": "missing_concept", "detail": "遗漏了关键概念 X"},
    {"type": "incorrect_relation", "detail": "关系 Y 描述不准确"},
    {"type": "low_confidence", "detail": "概念 Z 置信度过低"}
  ],
  "recommendation": "accept" | "retry" | "fail",
  "retry_hint": "如果建议重试，给出改进建议"
}

评估标准：
1. 完整性：是否遗漏对话中的关键概念（检查率 > 80% = 好）
2. 准确性：提取的关系是否正确反映了对话内容
3. 置信度：整体置信度是否合理

recommendation 判断：
- score >= 70 → "accept"
- score >= 40 且 issues <= 3 → "retry"
- score < 40 → "fail"
"""


@AgentRegistry.register("evaluation")
class EvaluationAgent(BaseAgent):
    name = "evaluation"
    description = "元评估提取质量与一致性"

    async def execute(self, context: AgentContext) -> AgentResult:
        extraction = context.intermediate_results.get("extraction")
        if not extraction:
            return AgentResult(
                success=True,
                data={"score": 100, "issues": [], "recommendation": "accept"},
            )

        conv_text = "\n".join(
            f"{m.role}: {m.content}" for m in context.messages
        )

        extraction_text = self._format_extraction(extraction)
        conflict_text = self._format_conflicts(
            context.intermediate_results.get("conflict_result")
        )

        messages = [
            {"role": "system", "content": EVAL_PROMPT},
            {
                "role": "user",
                "content": (
                    f"对话内容：\n{conv_text}\n\n"
                    f"提取结果：\n{extraction_text}\n\n"
                    f"冲突检测结果：\n{conflict_text}"
                ),
            },
        ]

        provider = ModelRouter.get_provider()
        try:
            result = await provider.chat_json(messages)
            if not isinstance(result, dict) or "score" not in result:
                return AgentResult(
                    success=False, error="Evaluation result missing 'score'"
                )
            return AgentResult(success=True, data=result)
        except Exception as e:
            self.log.error("Evaluation failed", e)
            return AgentResult(success=False, error=str(e))

    @staticmethod
    def _format_extraction(extraction: dict) -> str:
        lines = []
        for n in extraction.get("nodes", []):
            lines.append(
                f"- {n['name']} ({n.get('domain', '?')}, 置信度: {n.get('confidence', '?')})"
            )
        for e in extraction.get("edges", []):
            lines.append(f"- {e['from']} → {e['to']} [{e['relation_type']}]")
        return "\n".join(lines) or "无提取"

    @staticmethod
    def _format_conflicts(conflict_result: dict | None) -> str:
        if not conflict_result:
            return "未检测"
        if not conflict_result.get("has_conflict"):
            return "无冲突"
        lines = []
        for c in conflict_result.get("conflicts", []):
            lines.append(f"- [{c['severity']}] {c['detail']}")
        return "\n".join(lines)
