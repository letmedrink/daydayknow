from typing import Any, Dict, List, Optional

from .context import AgentContext
from .extraction_agent import ExtractionAgent
from .profile_agent import ProfileAgent
from .conflict_agent import ConflictAgent
from .evaluation_agent import EvaluationAgent
from ..utils.logger import create_module_logger

log = create_module_logger("agent.orchestrator")

# 懒导入 langgraph，未安装时降级为顺序执行
_LANGGRAPH_AVAILABLE = False


def _try_import_langgraph():
    global _LANGGRAPH_AVAILABLE
    try:
        from langgraph.graph import StateGraph, END, START
        import operator
        from typing import TypedDict, Annotated

        _LANGGRAPH_AVAILABLE = True
        return StateGraph, END, START, operator, TypedDict, Annotated
    except ImportError:
        _LANGGRAPH_AVAILABLE = False
        return None


# 尝试导入
_langgraph_imports = _try_import_langgraph()


async def _run_extraction(context: AgentContext) -> dict:
    agent = ExtractionAgent()
    result = await agent.execute(context)
    if result.success:
        return {"extraction": result.data}
    return {"errors": [f"extraction: {result.error}"]}


async def _run_profile(context: AgentContext) -> dict:
    agent = ProfileAgent()
    result = await agent.execute(context)
    if result.success:
        return {"profile_data": result.data}
    return {"errors": [f"profile: {result.error}"]}


async def _run_conflict(context: AgentContext) -> dict:
    agent = ConflictAgent()
    result = await agent.execute(context)
    if result.success:
        return {"conflicts": result.data}
    return {"errors": [f"conflict: {result.error}"]}


async def _run_evaluation(context: AgentContext) -> dict:
    agent = EvaluationAgent()
    result = await agent.execute(context)
    if result.success:
        return {"evaluation": result.data}
    return {"errors": [f"evaluation: {result.error}"]}


async def _run_sequential(
    context: AgentContext,
    existing_nodes: list | None,
    existing_edges: list | None,
) -> dict:
    """顺序执行后处理（langgraph 不可用时的降级方案）。"""
    context.metadata["existing_nodes"] = existing_nodes or []
    context.metadata["existing_edges"] = existing_edges or []

    errors: List[str] = []

    # 并行模拟：先提取、再画像
    extraction_result = await _run_extraction(context)
    errors.extend(extraction_result.get("errors", []))

    profile_result = await _run_profile(context)
    errors.extend(profile_result.get("errors", []))

    # 冲突检测（依赖提取结果）
    if extraction_result.get("extraction"):
        conflict_result = await _run_conflict(context)
        errors.extend(conflict_result.get("errors", []))
    else:
        conflict_result = {"conflicts": None}

    # 评估
    eval_result = await _run_evaluation(context)
    errors.extend(eval_result.get("errors", []))

    return {
        "extraction": extraction_result.get("extraction"),
        "profile_data": profile_result.get("profile_data"),
        "conflicts": conflict_result.get("conflicts"),
        "evaluation": eval_result.get("evaluation"),
        "errors": errors,
    }


def _build_langgraph_app():
    """构建 LangGraph 编排图（仅在 langgraph 可用时调用）。"""
    if not _langgraph_imports:
        return None

    StateGraph, END, START, operator, TypedDict, Annotated = _langgraph_imports

    class OrchestratorState(TypedDict):
        context: Any
        extraction: Optional[Dict[str, Any]]
        profile_data: Optional[Dict[str, Any]]
        conflicts: Optional[Dict[str, Any]]
        evaluation: Optional[Dict[str, Any]]
        errors: Annotated[List[str], operator.add]
        should_extract: bool

    async def extract_node(state):
        return await _run_extraction(state["context"])

    async def profile_update_node(state):
        return await _run_profile(state["context"])

    async def conflict_check_node(state):
        return await _run_conflict(state["context"])

    async def evaluate_node(state):
        return await _run_evaluation(state["context"])

    def after_evaluate(state):
        eval_result = state.get("evaluation")
        if eval_result and eval_result.get("recommendation") == "retry":
            return "retry"
        return "end"

    graph = StateGraph(OrchestratorState)
    graph.add_node("extract", extract_node)
    graph.add_node("profile_update", profile_update_node)
    graph.add_node("conflict_check", conflict_check_node)
    graph.add_node("evaluate", evaluate_node)

    graph.add_edge(START, "extract")
    graph.add_edge(START, "profile_update")
    graph.add_edge("extract", "conflict_check")
    graph.add_edge("conflict_check", "evaluate")
    graph.add_edge("profile_update", "evaluate")
    graph.add_conditional_edges(
        "evaluate", after_evaluate, {"retry": "extract", "end": END}
    )

    return graph.compile()


class PostProcessOrchestrator:
    """对话后处理编排器。在 chat 流式输出完成后运行。"""

    def __init__(self):
        self._langgraph_app = None
        if _LANGGRAPH_AVAILABLE:
            try:
                self._langgraph_app = _build_langgraph_app()
            except Exception as e:
                log.warn(f"LangGraph init failed, falling back to sequential: {e}")

    async def run(
        self,
        context: AgentContext,
        existing_nodes: list | None = None,
        existing_edges: list | None = None,
    ) -> dict:
        """执行后处理流水线，返回汇总结果。"""
        context.metadata["existing_nodes"] = existing_nodes or []
        context.metadata["existing_edges"] = existing_edges or []

        if self._langgraph_app:
            from typing import TypedDict

            initial_state = {
                "context": context,
                "extraction": None,
                "profile_data": None,
                "conflicts": None,
                "evaluation": None,
                "errors": [],
                "should_extract": True,
            }
            final_state = await self._langgraph_app.ainvoke(initial_state)
            return {
                "extraction": final_state.get("extraction"),
                "profile_data": final_state.get("profile_data"),
                "conflicts": final_state.get("conflicts"),
                "evaluation": final_state.get("evaluation"),
                "errors": final_state.get("errors", []),
            }
        else:
            return await _run_sequential(context, existing_nodes, existing_edges)
