"""llmwiki FastAPI application."""

import time
import uuid
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import chat, ingest, projects, research, reviews, wiki
from .api import settings as settings_api
from .config import settings
from .storage import FileStore
from .storage.project_store import ProjectStore
from .utils.logger import create_module_logger

log = create_module_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.global_store = FileStore(settings.DATA_DIR)
    app.state.project_store = ProjectStore(settings.DATA_DIR)
    log.logger.info("数据目录: %s", settings.DATA_DIR)
    yield


class RequestIDMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        request = Request(scope, receive)
        request_id = request.headers.get("X-Request-Id", str(uuid.uuid4())[:8])
        scope.setdefault("state", {})["request_id"] = request_id
        started = time.time()
        await self.app(scope, receive, send)
        if not request.url.path.startswith(("/health", "/docs", "/redoc", "/openapi")):
            log.logger.info(
                "%s %s [%.1fms]",
                request.method,
                request.url.path,
                (time.time() - started) * 1000,
                extra={"request_id": request_id, "method": request.method, "path": request.url.path},
            )


def error_response(status_code: int, detail: str, code: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"success": False, "error": detail, "code": code})


app = FastAPI(
    title="llmwiki API",
    description="AI-powered knowledge wiki backed by JSON and Markdown",
    version="3.0.0",
    lifespan=lifespan,
)


@app.exception_handler(HTTPException)
async def handle_http_error(_request: Request, exc: HTTPException):
    return error_response(exc.status_code, str(exc.detail), "http_error")


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"success": False, "error": "请求参数无效", "code": "validation_error", "details": exc.errors()},
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(_request: Request, exc: Exception):
    log.logger.error("未处理异常: %s", exc, exc_info=True)
    return error_response(500, "服务器内部错误", "internal_error")


app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-Id"],
)

app.include_router(projects.router, tags=["项目"])
app.include_router(chat.router, tags=["对话"])
app.include_router(wiki.router, tags=["Wiki"])
app.include_router(ingest.router, tags=["文档摄入"])
app.include_router(reviews.router, tags=["审阅项"])
app.include_router(research.router, tags=["深度研究"])
app.include_router(settings_api.router, tags=["设置"])


@app.get("/")
async def root():
    return {"success": True, "data": {"name": "llmwiki API", "version": "3.0.0", "docs": "/docs"}}


@app.get("/health")
async def health_check(request: Request):
    stored = request.app.state.global_store.get_settings()
    active_id = stored.get("activeProviderId")
    active_provider = stored.get("llmProviders", {}).get(active_id, {}) if active_id else {}
    search_config = stored.get("searchApiConfig", {})
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "checks": {
                "data_dir": "writable" if os.access(settings.DATA_DIR, os.R_OK | os.W_OK) else "unavailable",
                "llm": "configured" if active_provider.get("api_key") or settings.LLM_API_KEY else "not_configured",
                "search_api": search_config.get("provider") or settings.SEARCH_API_PROVIDER or "not_configured",
            },
        },
    }
