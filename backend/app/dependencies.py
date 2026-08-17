"""FastAPI dependency providers for global and project-scoped stores."""

from fastapi import HTTPException, Path, Request

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


def get_project_file_store(request: Request, project_id: str = Path(...)) -> FileStore:
    runtime = request.app.state.project_store.get_runtime(project_id)
    if runtime is None:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")
    file_store = runtime[0]
    if not getattr(file_store, "_ingest_recovered", False):
        file_store.recover_ingest_jobs()
        file_store.recover_research_jobs()
        file_store._ingest_recovered = True
    return file_store


def get_project_wiki_store(request: Request, project_id: str = Path(...)) -> WikiStore:
    runtime = request.app.state.project_store.get_runtime(project_id)
    if runtime is None:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")
    file_store, wiki_store = runtime
    if not getattr(file_store, "_ingest_recovered", False):
        file_store.recover_ingest_jobs()
        file_store.recover_research_jobs()
        file_store._ingest_recovered = True
    return wiki_store
