"""统一错误处理。"""
from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """应用自定义异常。"""

    def __init__(self, status_code: int, detail: str, code: str = "error"):
        self.status_code = status_code
        self.detail = detail
        self.code = code


class NotFoundError(AppError):
    def __init__(self, detail: str = "资源不存在"):
        super().__init__(404, detail, "not_found")


class BadRequestError(AppError):
    def __init__(self, detail: str = "请求参数错误"):
        super().__init__(400, detail, "bad_request")


class ForbiddenError(AppError):
    def __init__(self, detail: str = "无权访问"):
        super().__init__(403, detail, "forbidden")


async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "code": exc.code,
        },
    )
