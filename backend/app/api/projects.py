"""项目管理 API。"""
import io
import json
import shutil
import stat
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from ..dependencies import get_project_store

router = APIRouter(prefix="/api/projects")


class CreateProjectRequest(BaseModel):
    name: str
    path: Optional[str] = None


class DeleteProjectDataRequest(BaseModel):
    confirmation: str


PROJECT_SCHEMA_VERSION = 1
MAX_IMPORT_BYTES = 500 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 20_000


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


@router.get("/{project_id}/export")
async def export_project(project_id: str, project_store=Depends(get_project_store)):
    project = next((item for item in project_store.list_projects() if item["id"] == project_id), None)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    project_dir = Path(project["path"])
    buffer = io.BytesIO()
    manifest = {
        "schemaVersion": PROJECT_SCHEMA_VERSION,
        "name": project["name"],
        "exportedAt": datetime.now(timezone.utc).isoformat(),
    }
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("llmwiki-project.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for path in project_dir.rglob("*"):
            if path.is_file() and not path.is_symlink():
                rel = path.relative_to(project_dir)
                if any(part.startswith(".") and part != ".llmwiki-project.json" for part in rel.parts):
                    continue
                archive.write(path, Path("project") / rel)
    buffer.seek(0)
    encoded_name = quote(f"{project['name'] or 'llmwiki-project'}.zip")
    disposition = f"attachment; filename=llmwiki-project.zip; filename*=UTF-8''{encoded_name}"
    return StreamingResponse(buffer, media_type="application/zip", headers={"Content-Disposition": disposition})


@router.post("/import")
async def import_project(
    archive: UploadFile = File(...), name: str | None = Form(None),
    project_store=Depends(get_project_store),
):
    payload = await archive.read(MAX_IMPORT_BYTES + 1)
    if len(payload) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="项目归档超过 500MB 上限")
    try:
        package = zipfile.ZipFile(io.BytesIO(payload))
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=400, detail="不是有效的 ZIP 项目归档") from exc
    infos = package.infolist()
    if len(infos) > MAX_ARCHIVE_ENTRIES or sum(info.file_size for info in infos) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="项目归档展开后过大")
    try:
        manifest = json.loads(package.read("llmwiki-project.json"))
    except (KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="缺少有效的 llmwiki-project.json") from exc
    if manifest.get("schemaVersion") != PROJECT_SCHEMA_VERSION:
        raise HTTPException(status_code=400, detail=f"不支持的数据版本: {manifest.get('schemaVersion')}")

    with tempfile.TemporaryDirectory(prefix="llmwiki-import-") as temp_name:
        temp_root = Path(temp_name)
        for info in infos:
            member = Path(info.filename)
            if info.filename == "llmwiki-project.json" or member.parts[:1] != ("project",):
                continue
            relative = Path(*member.parts[1:])
            if not relative.parts or relative.is_absolute() or ".." in relative.parts:
                raise HTTPException(status_code=400, detail="归档包含非法路径")
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise HTTPException(status_code=400, detail="归档不允许包含符号链接")
            target = temp_root / relative
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with package.open(info) as source, target.open("wb") as destination:
                    shutil.copyfileobj(source, destination)
        project_name = (name or manifest.get("name") or "导入项目").strip()
        if not project_name:
            raise HTTPException(status_code=400, detail="项目名称不能为空")
        project = project_store.create_project(project_name)
        try:
            shutil.copytree(temp_root, project["path"], dirs_exist_ok=True)
            Path(project["path"], ".llmwiki-project.json").write_text(
                json.dumps({"schemaVersion": PROJECT_SCHEMA_VERSION}, indent=2), encoding="utf-8",
            )
        except BaseException:
            project_store.delete_project_data(project["id"], project["name"])
            raise
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
