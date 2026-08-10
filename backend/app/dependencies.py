"""FastAPI dependency providers for global and project-scoped stores."""

from fastapi import Depends, HTTPException, Path, Request

from .storage.file_store import FileStore
from .storage.wiki_store import WikiStore


def get_global_store(request: Request) -> FileStore:
    """Return the global store used by settings and the user profile."""
    return request.app.state.global_store


def get_project_store(request: Request):
    return request.app.state.project_store


def get_project_dir(request: Request, project_id: str = Path(...)):
    project_dir = request.app.state.project_store.get_project_dir(project_id)
    if not project_dir:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")
    return project_dir


def get_project_file_store(project_dir=Depends(get_project_dir)) -> FileStore:
    return FileStore(project_dir)


def get_project_wiki_store(project_dir=Depends(get_project_dir)) -> WikiStore:
    return WikiStore(project_dir)
