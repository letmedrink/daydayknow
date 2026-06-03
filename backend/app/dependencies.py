from fastapi import Request
from .config import settings


def get_file_store(request: Request):
    """获取文件存储实例。"""
    return request.app.state.file_store


def get_wiki_store(request: Request):
    """获取 Wiki 存储实例。"""
    return request.app.state.wiki_store


def get_current_user() -> str:
    """获取当前用户 ID（个人使用，固定值）。"""
    return settings.USER_ID
