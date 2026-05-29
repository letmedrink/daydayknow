import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from .api import chat, conversations, import_
from .config import settings
from .errors import AppError, app_error_handler
from .models.responses import HealthResponse
from .utils.logger import create_module_logger

log = create_module_logger("api")


limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # 关闭 Redis/ARQ 连接
    from .tasks.queue import close_connections
    await close_connections()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """为每个请求注入 request_id 并记录日志。"""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-Id", str(uuid.uuid4())[:8])
        request.state.request_id = request_id

        start = time.time()
        response = await call_next(request)
        duration_ms = round((time.time() - start) * 1000, 1)

        response.headers["X-Request-Id"] = request_id

        # 跳过健康检查和静态文件日志
        if not request.url.path.startswith(("/health", "/docs", "/redoc", "/openapi")):
            log.logger.info(
                f"{request.method} {request.url.path} {response.status_code}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )

        return response


app = FastAPI(
    title="知微 API",
    description="格物致知，见微知著 — AI 知识学习平台",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter

# 注册异常处理器
app.add_exception_handler(AppError, app_error_handler)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"success": False, "error": f"请求过于频繁，请稍后再试。限制: {exc.detail}", "code": "rate_limited"},
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "服务器内部错误", "code": "internal_error"},
    )


# 中间件
app.add_middleware(RequestIDMiddleware)

# CORS
cors_origins = []
if settings.APP_URL:
    cors_origins.append(settings.APP_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-User-Id", "X-Request-Id"],
)

# 路由分组
app.include_router(chat.router, tags=["对话 & 知识图谱"])
app.include_router(conversations.router, tags=["对话管理"])
app.include_router(import_.router, tags=["内容导入"])


@app.get("/", tags=["系统"])
async def root():
    return {
        "message": "知微 API",
        "version": "2.0.0",
        "docs": "/docs"
    }


@app.get("/health", tags=["系统"], response_model=HealthResponse)
async def health_check():
    checks = {}

    # 数据库连接
    if settings.DATABASE_URL:
        try:
            from sqlalchemy import text
            from sqlalchemy.ext.asyncio import create_async_engine
            engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            checks["database"] = "ok"
            await engine.dispose()
        except Exception as e:
            checks["database"] = f"error: {e}"
    else:
        checks["database"] = "not_configured"

    # Redis 连接
    if settings.REDIS_URL:
        try:
            import redis.asyncio as aioredis
            r = aioredis.from_url(settings.REDIS_URL)
            await r.ping()
            checks["redis"] = "ok"
            await r.close()
        except Exception as e:
            checks["redis"] = f"error: {e}"
    else:
        checks["redis"] = "not_configured"

    # LLM 连通性
    if settings.LLM_API_KEY:
        checks["llm"] = f"configured ({settings.LLM_PROVIDER})"
    else:
        checks["llm"] = "not_configured"

    # Embedding
    checks["embedding"] = settings.EMBEDDING_PROVIDER

    all_ok = all(
        v in ("ok", "not_configured") or v.startswith("configured")
        for v in checks.values()
    )

    return {
        "status": "healthy" if all_ok else "degraded",
        "mock_mode": settings.MOCK_MODE,
        "checks": checks,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
