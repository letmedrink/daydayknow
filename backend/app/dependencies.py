from fastapi import Request, Query, HTTPException
from .config import settings
from .storage.wiki_store import WikiStore
from .storage.file_store import FileStore


def get_file_store(request: Request):
    """获取全局文件存储实例（设置等全局数据）。"""
    return request.app.state.file_store


def get_wiki_store(request: Request):
    """获取全局 Wiki 存储实例。"""
    return request.app.state.wiki_store


def get_project_store(request: Request):
    """获取项目管理实例。"""
    return request.app.state.project_store


def get_active_wiki_store(request: Request, project_id: str = Query(...)):
    """获取当前项目的 Wiki 存储实例。project_id 为必填参数。"""
    ps = request.app.state.project_store
    project_dir = ps.get_project_dir(project_id)
    if not project_dir:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")
    return WikiStore(project_dir)


def get_active_file_store(request: Request, project_id: str = Query(...)):
    """获取当前项目的文件存储实例。project_id 为必填参数。"""
    ps = request.app.state.project_store
    project_dir = ps.get_project_dir(project_id)
    if not project_dir:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")
    return FileStore(project_dir)


def get_current_user() -> str:
    """获取当前用户 ID（个人使用，固定值）。"""
    return settings.USER_ID
