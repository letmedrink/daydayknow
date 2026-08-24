"""Immutable raw source browsing and download API."""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse

from ..dependencies import get_global_store, get_project_file_store, get_project_source_store, get_project_wiki_store
from ..storage import FileStore, WikiStore

router = APIRouter(prefix="/api/projects/{project_id}/sources")


@router.get("")
async def list_sources(source_store=Depends(get_project_source_store)):
    return {"success": True, "data": source_store.list()}


@router.get("/{source_id}")
async def get_source(source_id: str, source_store=Depends(get_project_source_store)):
    source = source_store.get(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="来源不存在")
    return {"success": True, "data": source}


@router.get("/{source_id}/original")
async def download_source(source_id: str, source_store=Depends(get_project_source_store)):
    try:
        path = source_store.original_path(source_id)
        source = source_store.get(source_id) or {}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(path, media_type=source.get("mimeType"), filename=source.get("filename") or path.name)


@router.get("/{source_id}/extraction")
async def get_extraction(
    source_id: str,
    version: int | None = Query(None),
    source_store=Depends(get_project_source_store),
):
    try:
        content = source_store.read_extraction(source_id, version)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PlainTextResponse(content, media_type="text/markdown; charset=utf-8")


@router.post("/{source_id}/ingest")
async def reingest_source(
    source_id: str,
    source_store=Depends(get_project_source_store),
    global_store: FileStore = Depends(get_global_store),
    file_store: FileStore = Depends(get_project_file_store),
    wiki_store: WikiStore = Depends(get_project_wiki_store),
):
    source = source_store.get(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="来源不存在")
    payload = source_store.original_path(source_id).read_bytes()
    job = file_store.create_ingest_job(source["filename"], payload, force=True)
    job = file_store.update_ingest_job(job["id"], sourceId=source_id) or job
    from .ingest import _start_job, _stream_job
    task, queue = _start_job(job, file_store, wiki_store, global_store)
    return _stream_job(task, queue, file_store, job["id"])
