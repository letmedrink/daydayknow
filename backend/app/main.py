import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import chat, wiki, ingest, reviews, research
from .api import settings as settings_api
from .config import settings
from .errors import AppError, app_error_handler
from .models.responses import HealthResponse
from .storage import FileStore, WikiStore
from .utils.logger import create_module_logger

log = create_module_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 初始化存储
    app.state.file_store = FileStore(settings.DATA_DIR)
    app.state.wiki_store = WikiStore(settings.DATA_DIR)
    log.logger.info(f"数据目录: {settings.DATA_DIR}")
    yield


class RequestIDMiddleware:
    """为每个请求注入 request_id 并记录日志。"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        request = Request(scope, receive)
        request_id = request.headers.get("X-Request-Id", str(uuid.uuid4())[:8])
        scope["state"] = {"request_id": request_id}

        start = time.time()
        response = await self.app(scope, receive, send)
        duration_ms = round((time.time() - start) * 1000, 1)

        if not request.url.path.startswith(("/health", "/docs", "/redoc", "/openapi")):
            log.logger.info(
                f"{request.method} {request.url.path} [{duration_ms}ms]",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                },
            )

        return response


app = FastAPI(
    title="知微 API",
    description="格物致知，见微知著 — AI 知识学习平台",
    version="3.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# 异常处理器
@app.exception_handler(AppError)
async def app_error_handler_wrapper(request: Request, exc: AppError):
    return await app_error_handler(request, exc)


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    log.logger.error(f"未处理异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "服务器内部错误", "code": "internal_error"},
    )


# 中间件
app.add_middleware(RequestIDMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-Id"],
)


def get_file_store(request: Request) -> FileStore:
    return request.app.state.file_store


def get_wiki_store(request: Request) -> WikiStore:
    return request.app.state.wiki_store


# 路由分组
app.include_router(chat.router, tags=["对话"])
app.include_router(wiki.router, tags=["Wiki"])
app.include_router(ingest.router, tags=["文档摄入"])
app.include_router(reviews.router, tags=["审阅项"])
app.include_router(research.router, tags=["深度研究"])
app.include_router(settings_api.router, tags=["设置"])


@app.get("/", tags=["系统"])
async def root():
    return {"message": "知微 API", "version": "3.0.0", "docs": "/docs"}


@app.get("/health", tags=["系统"], response_model=HealthResponse)
async def health_check():
    return {
        "status": "healthy",
        "checks": {
            "data_dir": settings.DATA_DIR,
            "llm": f"configured ({settings.LLM_PROVIDER})" if settings.LLM_API_KEY else "not_configured",
            "search_api": settings.SEARCH_API_PROVIDER or "not_configured",
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
