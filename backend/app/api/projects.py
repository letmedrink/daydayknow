"""项目管理 API。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..dependencies import get_project_store

router = APIRouter(prefix="/api/projects")


class CreateProjectRequest(BaseModel):
    name: str
    path: Optional[str] = None


class DeleteProjectDataRequest(BaseModel):
    confirmation: str


@router.get("")
async def list_projects(project_store=Depends(get_project_store)):
    projects = project_store.list_projects()
    return {"success": True, "data": projects}


@router.post("")
async def create_project(req: CreateProjectRequest, project_store=Depends(get_project_store)):
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="项目名称不能为空")
    project = project_store.create_project(req.name.strip(), req.path)
    return {"success": True, "data": project}


@router.delete("/{project_id}")
async def delete_project(project_id: str, project_store=Depends(get_project_store)):
    if not project_store.delete_project(project_id):
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"success": True}


@router.delete("/{project_id}/data")
async def delete_project_data(
    project_id: str,
    req: DeleteProjectDataRequest,
    project_store=Depends(get_project_store),
):
    try:
        deleted = project_store.delete_project_data(project_id, req.confirmation)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"success": True}
