from .base import BaseAgent, AgentResult
from .context import AgentContext
from .registry import AgentRegistry
from ..services.llm.router import ModelRouter


CONFLICT_PROMPT = """你是一个知识一致性检测专家。

给定新提取的知识概念和已有知识图谱，检测是否存在矛盾。

输出JSON格式：
{
  "conflicts": [
    {
      "type": "semantic_contradiction" | "attribute_inconsistency" | "opposite_relation",
      "new_node": "新概念名称",
      "existing_node": "已有概念名称",
      "detail": "矛盾描述",
      "severity": "high" | "medium" | "low",
      "suggestion": "处理建议"
    }
  ],
  "has_conflict": true/false
}

检测规则：
1. 语义矛盾：新概念定义与已有概念冲突（如 A 说 B 是子集，但已有记录说 B 是子集）
2. 属性不一致：同一概念的领域或描述发生冲突
3. 关系相反：新提取的关系方向与已有关系相反（如之前是 A→B is-a，现在是 B→A is-a）

如果新知识与已有知识互补而非矛盾，不要标记为冲突。
如果没有矛盾，返回 {"conflicts": [], "has_conflict": false}"""


@AgentRegistry.register("conflict")
class ConflictAgent(BaseAgent):
    name = "conflict"
    description = "检测新提取知识与已有图谱的矛盾"

    async def execute(self, context: AgentContext) -> AgentResult:
        extraction = context.intermediate_results.get("extraction")
        if not extraction:
            return AgentResult(success=True, data={"conflicts": [], "has_conflict": False})

        # 从 metadata 获取已有图谱数据
        existing_nodes = context.metadata.get("existing_nodes", [])
        existing_edges = context.metadata.get("existing_edges", [])

        if not existing_nodes:
            return AgentResult(success=True, data={"conflicts": [], "has_conflict": False})

        new_summary = self._format_extraction(extraction)
        existing_summary = self._format_graph(existing_nodes, existing_edges)

        messages = [
            {"role": "system", "content": CONFLICT_PROMPT},
            {
                "role": "user",
                "content": f"新提取的知识：\n{new_summary}\n\n已有知识图谱：\n{existing_summary}",
            },
        ]

        provider = ModelRouter.get_provider()
        try:
            result = await provider.chat_json(messages)
            if not isinstance(result, dict) or "conflicts" not in result:
                return AgentResult(
                    success=False, error="Conflict result missing 'conflicts' field"
                )
            return AgentResult(success=True, data=result)
        except Exception as e:
            self.log.error("Conflict detection failed", e)
            return AgentResult(success=False, error=str(e))

    @staticmethod
    def _format_extraction(extraction: dict) -> str:
        lines = []
        for n in extraction.get("nodes", []):
            lines.append(
                f"- {n['name']} (领域: {n.get('domain', '?')}, "
                f"描述: {n.get('description', '?')}, 置信度: {n.get('confidence', '?')})"
            )
        for e in extraction.get("edges", []):
            lines.append(
                f"- {e['from']} --[{e['relation_type']}]--> {e['to']} (强度: {e.get('strength', '?')})"
            )
        return "\n".join(lines) or "无新提取"

    @staticmethod
    def _format_graph(nodes: list, edges: list) -> str:
        lines = []
        name_map = {n["id"]: n["name"] for n in nodes}
        for n in nodes:
            lines.append(
                f"- {n['name']} (领域: {n.get('domain', '?')}, "
                f"描述: {n.get('description', '?')})"
            )
        for e in edges:
            from_name = name_map.get(e["from_node_id"], e["from_node_id"])
            to_name = name_map.get(e["to_node_id"], e["to_node_id"])
            lines.append(f"- {from_name} --[{e['relation_type']}]--> {to_name}")
        return "\n".join(lines) or "图谱为空"
