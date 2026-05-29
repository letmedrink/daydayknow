"""ARQ Worker 定义 — 后台任务处理。"""
from typing import Any, Dict

from ..agents.context import AgentContext, Message
from ..agents.orchestrator import PostProcessOrchestrator
from ..db.factory import get_graph_store
from ..config import settings
from ..utils.logger import create_module_logger

log = create_module_logger("tasks.worker")


async def post_process_task(ctx: Any, conversation_id: str, user_id: str) -> dict:
    """ARQ 后台任务：执行对话后处理流水线。

    Args:
        conversation_id: 对话 ID
        user_id: 用户 ID
    """
    graph_store = get_graph_store()
    orchestrator = PostProcessOrchestrator()

    # 重建 context
    server_messages = await graph_store.get_messages(conversation_id)
    messages = [Message(role=m["role"], content=m["content"]) for m in server_messages]
    context = AgentContext(
        conversation_id=conversation_id,
        user_id=user_id,
        messages=messages,
    )

    existing_nodes = await graph_store.get_user_nodes(user_id)
    existing_edges = await graph_store.get_user_edges(user_id)

    result = await orchestrator.run(context, existing_nodes, existing_edges)

    # 存储提取结果
    extraction = result.get("extraction")
    stored_nodes, stored_edges = [], []
    if extraction:
        stored = await graph_store.store_extraction(
            user_id=user_id,
            extraction=extraction,
            source_ref=conversation_id,
        )
        stored_nodes = stored["nodes"]
        stored_edges = stored["edges"]

    # 存储画像
    profile_data = result.get("profile_data")
    if profile_data:
        await graph_store.save_profile(user_id, profile_data)

    log.info(f"Post-process complete for conversation={conversation_id}")

    return {
        "extraction": extraction,
        "nodes": stored_nodes,
        "edges": stored_edges,
        "conflicts": result.get("conflicts"),
        "profile_updated": profile_data is not None,
        "errors": result.get("errors", []),
    }


class WorkerSettings:
    """ARQ Worker 配置。"""
    functions = [post_process_task]
    redis_settings = None  # 由 startup 中设置

    async def startup(ctx: dict):
        log.info("ARQ worker started")

    async def shutdown(ctx: dict):
        log.info("ARQ worker stopped")


def get_redis_settings():
    """从配置获取 Redis 连接设置。"""
    from arq.connections import RedisSettings
    return RedisSettings.from_dsn(settings.REDIS_URL)
