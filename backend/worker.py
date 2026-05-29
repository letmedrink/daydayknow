"""ARQ Worker 启动脚本。

用法：
  python worker.py              # 使用默认配置
  REDIS_URL=redis://localhost python worker.py  # 指定 Redis

需要先启动 Redis 服务。
"""
import asyncio
from arq import create_pool
from arq.connections import RedisSettings

from app.config import settings
from app.tasks.worker import post_process_task
from app.utils.logger import create_module_logger

log = create_module_logger("worker")


async def main():
    if not settings.REDIS_URL:
        log.error("REDIS_URL not set, cannot start worker")
        return

    rs = RedisSettings.from_dsn(settings.REDIS_URL)
    log.info(f"Starting ARQ worker, Redis: {settings.REDIS_URL}")

    from arq import run_worker
    from arq.worker import Function

    await run_worker(
        [Function(post_process_task, name="post_process_task")],
        redis_settings=rs,
    )


if __name__ == "__main__":
    asyncio.run(main())
