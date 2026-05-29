"""任务队列管理 — ARQ 模式 + 内联降级。"""
import json
import uuid
from typing import Optional

from ..config import settings
from ..utils.logger import create_module_logger

log = create_module_logger("tasks.queue")

_arq_pool = None
_redis_client = None


async def _get_arq_pool():
    """懒加载 ARQ 连接池。"""
    global _arq_pool
    if _arq_pool is None:
        from arq import create_pool
        from arq.connections import RedisSettings
        rs = RedisSettings.from_dsn(settings.REDIS_URL)
        _arq_pool = await create_pool(rs)
    return _arq_pool


async def _get_redis():
    """懒加载 Redis 客户端（用于存储任务结果）。"""
    global _redis_client
    if _redis_client is None:
        import redis.asyncio as aioredis
        _redis_client = aioredis.from_url(settings.REDIS_URL)
    return _redis_client


async def close_connections():
    """关闭连接池。"""
    global _arq_pool, _redis_client
    if _arq_pool:
        await _arq_pool.close()
        _arq_pool = None
    if _redis_client:
        await _redis_client.close()
        _redis_client = None


async def enqueue_post_process(conversation_id: str, user_id: str) -> dict:
    """将后处理任务加入队列。

    Redis 可用时使用 ARQ 异步处理，否则同步执行。

    Returns:
        {"task_id": str, "status": "queued"|"completed", "result": dict|None}
    """
    if not settings.REDIS_URL:
        return await _run_inline(conversation_id, user_id)

    try:
        pool = await _get_arq_pool()
        job = await pool.enqueue_job(
            "post_process_task",
            conversation_id=conversation_id,
            user_id=user_id,
            _job_id=f"pp:{conversation_id}",
        )
        if job:
            log.info(f"Enqueued post-process task {job.job_id}")
            return {"task_id": job.job_id, "status": "queued", "result": None}
        else:
            log.warn("ARQ enqueue returned None, falling back to inline")
            return await _run_inline(conversation_id, user_id)
    except Exception as e:
        log.warn(f"ARQ enqueue failed: {e}, falling back to inline")
        return await _run_inline(conversation_id, user_id)


async def get_task_status(task_id: str) -> Optional[dict]:
    """查询任务状态。

    Returns:
        {"status": "queued"|"in_progress"|"completed"|"failed", "result": dict|None}
        或 None（任务不存在）
    """
    if not settings.REDIS_URL:
        return None

    try:
        redis = await _get_redis()
        raw = await redis.get(f"task:result:{task_id}")
        if raw:
            return json.loads(raw)

        pool = await _get_arq_pool()
        job = await pool.job(job_id=task_id)
        if job:
            if job.status == "queued":
                return {"status": "queued", "result": None}
            elif job.status == "in_progress":
                return {"status": "in_progress", "result": None}
            elif job.status == "complete":
                return {"status": "completed", "result": job.result}
            else:
                return {"status": "failed", "result": None}
        return None
    except Exception as e:
        log.warn(f"Task status check failed: {e}")
        return None


async def save_task_result(task_id: str, result: dict, ttl: int = 3600):
    """保存任务结果到 Redis（由 ARQ worker 调用或内联模式使用）。"""
    if not settings.REDIS_URL:
        return
    try:
        redis = await _get_redis()
        await redis.setex(
            f"task:result:{task_id}",
            ttl,
            json.dumps({"status": "completed", "result": result}),
        )
    except Exception as e:
        log.warn(f"Save task result failed: {e}")


async def _run_inline(conversation_id: str, user_id: str) -> dict:
    """同步执行后处理（无 Redis 降级方案）。"""
    from .worker import post_process_task

    log.info(f"Running post-process inline for conversation={conversation_id}")
    result = await post_process_task(
        ctx=None,
        conversation_id=conversation_id,
        user_id=user_id,
    )

    task_id = f"inline:{conversation_id}"
    return {"task_id": task_id, "status": "completed", "result": result}
