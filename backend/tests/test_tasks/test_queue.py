import pytest
from unittest.mock import patch, AsyncMock

from app.tasks.queue import enqueue_post_process, get_task_status


class TestInlineFallback:
    """无 Redis 时的内联降级测试。"""

    @pytest.mark.asyncio
    async def test_inline_returns_completed(self):
        """REDIS_URL 为空时应同步执行并返回 completed。"""
        from app.tasks import queue as queue_mod
        from app.config import settings

        old = settings.REDIS_URL
        settings.REDIS_URL = ""
        try:
            result = await enqueue_post_process("conv-test", "user-test")
            assert result["status"] == "completed"
            assert result["task_id"].startswith("inline:")
            assert "result" in result
        finally:
            settings.REDIS_URL = old

    @pytest.mark.asyncio
    async def test_inline_result_structure(self):
        """内联结果应包含提取、冲突、画像字段。"""
        from app.tasks import queue as queue_mod
        from app.config import settings

        old = settings.REDIS_URL
        settings.REDIS_URL = ""
        try:
            result = await enqueue_post_process("conv-struct", "user-struct")
            data = result["result"]
            assert "extraction" in data
            assert "nodes" in data
            assert "edges" in data
            assert "conflicts" in data
            assert "profile_updated" in data
            assert "errors" in data
        finally:
            settings.REDIS_URL = old

    @pytest.mark.asyncio
    async def test_get_task_status_no_redis(self):
        """无 Redis 时 task status 返回 None。"""
        from app.config import settings

        old = settings.REDIS_URL
        settings.REDIS_URL = ""
        try:
            result = await get_task_status("any-task-id")
            assert result is None
        finally:
            settings.REDIS_URL = old


class TestWorkerFunction:
    """Worker post_process_task 直接调用测试。"""

    @pytest.mark.asyncio
    async def test_worker_with_empty_messages(self):
        """空对话场景下 worker 不应崩溃。"""
        from app.tasks.worker import post_process_task
        from app.db.factory import get_graph_store

        store = get_graph_store()
        # 创建对话但不添加消息
        conv = await store.create_conversation(user_id="worker-test-user")
        conv_id = conv["id"]

        result = await post_process_task(
            ctx=None,
            conversation_id=conv_id,
            user_id="worker-test-user",
        )

        assert "extraction" in result
        assert "errors" in result
