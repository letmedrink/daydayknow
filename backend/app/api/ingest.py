"""Durable, review-before-commit document ingestion API."""

import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..config import settings
from ..dependencies import get_global_store, get_project_file_store, get_project_wiki_store
from ..ingest.pipeline import PIPELINE_VERSION, run_ingest_pipeline
from ..storage import FileStore, WikiStore

router = APIRouter(prefix="/api/projects/{project_id}/ingest")
_RUNNING: dict[str, asyncio.Task] = {}


class ProposalInput(BaseModel):
    path: str
    content: str
    merge: bool = True


class AcceptIngestRequest(BaseModel):
    proposals: list[ProposalInput] | None = None


class RegenerateIngestRequest(BaseModel):
    feedback: str


async def _read_upload(file: UploadFile) -> bytes:
    chunks: list[bytes] = []
    size = 0
    while chunk := await file.read(1024 * 1024):
        size += len(chunk)
        if size > settings.MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail=f"文件超过 {settings.MAX_UPLOAD_BYTES // (1024 * 1024)}MB 上限")
        chunks.append(chunk)
    return b"".join(chunks)


def _job_key(file_store: FileStore, job_id: str) -> str:
    return f"{file_store.data_dir.resolve()}::{job_id}"


def _public_job(job: dict) -> dict:
    public = dict(job)
    result = public.get("result")
    if result:
        public["result"] = {key: value for key, value in result.items() if key != "source_hash"}
    return public


def _start_job(
    job: dict,
    file_store: FileStore,
    wiki_store: WikiStore,
    global_store: FileStore,
) -> tuple[asyncio.Task, asyncio.Queue]:
    queue: asyncio.Queue = asyncio.Queue()
    job_id = job["id"]
    stage_dir = file_store.data_dir / "ingest-jobs" / job_id / "stage"

    async def on_progress(step, progress, message):
        updated = file_store.update_ingest_job(
            job_id, status="running", step=step, progress=progress, message=message,
        )
        if updated and updated.get("status") == "cancelled":
            raise asyncio.CancelledError
        await queue.put({"type": "progress", "job_id": job_id, "step": step, "progress": progress, "message": message})

    async def run():
        try:
            file_store.update_ingest_job(job_id, status="running", step="parse", progress=0)
            result = await run_ingest_pipeline(
                job["filename"], file_store.ingest_job_source(job_id), file_store, wiki_store, global_store,
                progress_callback=on_progress, force=bool(job.get("force")), auto_commit=False, stage_dir=stage_dir,
                custom_instructions=str(job.get("instructions") or ""),
            )
            if result.get("cached"):
                status = "accepted"
                result["status"] = status
                (file_store.data_dir / "ingest-jobs" / job_id / "source.bin").unlink(missing_ok=True)
            else:
                status = "awaiting_review"
            updated = file_store.update_ingest_job(
                job_id, status=status, step="review" if status == "awaiting_review" else "done",
                progress=1, message="请预览后接受或拒绝" if status == "awaiting_review" else "已命中摄入缓存",
                result=result,
            )
            await queue.put({"type": "done", "job": _public_job(updated or {}), "result": result})
        except asyncio.CancelledError:
            file_store.update_ingest_job(job_id, status="cancelled", step="cancelled", message="任务已取消")
            await queue.put({"type": "error", "error": "摄入已取消", "code": "cancelled"})
        except Exception as exc:
            file_store.update_ingest_job(job_id, status="failed", step="error", message=str(exc))
            await queue.put({"type": "error", "error": str(exc), "code": "ingest_failed"})
        finally:
            _RUNNING.pop(_job_key(file_store, job_id), None)
            await queue.put(None)

    task = asyncio.create_task(run())
    _RUNNING[_job_key(file_store, job_id)] = task
    return task, queue


def _stream_job(task: asyncio.Task, queue: asyncio.Queue, file_store: FileStore, job_id: str):
    async def event_stream():
        completed = False
        try:
            while True:
                event = await queue.get()
                if event is None:
                    completed = True
                    break
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        finally:
            if not completed and not task.done():
                task.cancel()
                file_store.update_ingest_job(job_id, status="cancelled", step="cancelled", message="客户端已断开")
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"})


@router.post("")
async def ingest_file(
    file: UploadFile = File(...), force: bool = Form(False),
    global_store: FileStore = Depends(get_global_store),
    file_store: FileStore = Depends(get_project_file_store),
    wiki_store: WikiStore = Depends(get_project_wiki_store),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名为空")
    content = await _read_upload(file)
    job = file_store.create_ingest_job(file.filename, content, force)
    task, queue = _start_job(job, file_store, wiki_store, global_store)
    return _stream_job(task, queue, file_store, job["id"])


@router.get("/jobs")
async def list_jobs(file_store: FileStore = Depends(get_project_file_store)):
    return {"success": True, "data": [_public_job(job) for job in file_store.list_ingest_jobs()]}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, file_store: FileStore = Depends(get_project_file_store)):
    job = file_store.get_ingest_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="摄入任务不存在")
    return {"success": True, "data": _public_job(job)}


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str, file_store: FileStore = Depends(get_project_file_store)):
    try:
        deleted = file_store.delete_ingest_job(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="摄入任务不存在")
    return {"success": True}


@router.post("/jobs/{job_id}/retry")
async def retry_job(
    job_id: str, global_store: FileStore = Depends(get_global_store),
    file_store: FileStore = Depends(get_project_file_store),
    wiki_store: WikiStore = Depends(get_project_wiki_store),
):
    job = file_store.get_ingest_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="摄入任务不存在")
    if job.get("status") not in {"failed", "cancelled", "interrupted"}:
        raise HTTPException(status_code=409, detail="当前任务状态不可重试")
    task, queue = _start_job(job, file_store, wiki_store, global_store)
    return _stream_job(task, queue, file_store, job_id)


@router.post("/jobs/{job_id}/regenerate")
async def regenerate_job(
    job_id: str, req: RegenerateIngestRequest,
    global_store: FileStore = Depends(get_global_store),
    file_store: FileStore = Depends(get_project_file_store),
    wiki_store: WikiStore = Depends(get_project_wiki_store),
):
    job = file_store.get_ingest_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="摄入任务不存在")
    if job.get("status") not in {"awaiting_review", "failed", "cancelled", "interrupted"}:
        raise HTTPException(status_code=409, detail="当前任务状态不可重新生成")
    feedback = req.feedback.strip()
    if not feedback:
        raise HTTPException(status_code=400, detail="请填写重新生成要求")
    try:
        file_store.ingest_job_source(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=409, detail="原始文件已清理，无法重新生成") from exc
    updated = file_store.update_ingest_job(
        job_id, status="pending", step="queued", progress=0, force=True,
        instructions=feedback, result=None, message="按反馈重新生成",
    )
    task, queue = _start_job(updated or job, file_store, wiki_store, global_store)
    return _stream_job(task, queue, file_store, job_id)


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str, file_store: FileStore = Depends(get_project_file_store)):
    job = file_store.get_ingest_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="摄入任务不存在")
    task = _RUNNING.get(_job_key(file_store, job_id))
    if task and not task.done():
        task.cancel()
    updated = file_store.update_ingest_job(job_id, status="cancelled", step="cancelled", message="任务已取消")
    return {"success": True, "data": _public_job(updated or job)}


def _copy_staged_media(file_store: FileStore, wiki_store: WikiStore, job_id: str, media_files: list[str]) -> list[tuple[Path, bytes | None]]:
    snapshots = []
    stage_root = file_store.data_dir / "ingest-jobs" / job_id / "stage"
    try:
        for rel_path in media_files:
            source = stage_root / rel_path
            target = wiki_store.wiki_dir / rel_path
            if not source.exists():
                continue
            original = target.read_bytes() if target.exists() else None
            snapshots.append((target, original))
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(source.read_bytes())
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, target)
            except BaseException:
                Path(temp_name).unlink(missing_ok=True)
                raise
        return snapshots
    except BaseException:
        _restore_media(snapshots)
        raise


def _restore_media(snapshots: list[tuple[Path, bytes | None]]):
    for target, original in snapshots:
        if original is None:
            target.unlink(missing_ok=True)
        else:
            target.write_bytes(original)


@router.post("/jobs/{job_id}/accept")
async def accept_job(
    job_id: str, req: AcceptIngestRequest | None = None,
    file_store: FileStore = Depends(get_project_file_store),
    wiki_store: WikiStore = Depends(get_project_wiki_store),
):
    job = file_store.get_ingest_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="摄入任务不存在")
    if job.get("status") != "awaiting_review":
        raise HTTPException(status_code=409, detail="任务不在待审核状态")
    result = job.get("result") or {}
    original_proposals = result.get("proposals", [])
    proposals = original_proposals
    if req and req.proposals is not None:
        allowed = {page["path"]: page for page in original_proposals}
        proposals = []
        for submitted in req.proposals:
            if submitted.path not in allowed:
                raise HTTPException(status_code=400, detail=f"页面不属于该摄入任务: {submitted.path}")
            proposals.append({**allowed[submitted.path], "content": submitted.content, "merge": submitted.merge})
    if not proposals:
        raise HTTPException(status_code=400, detail="至少选择一个页面写入")
    page_snapshots = wiki_store.snapshot_pages([page["path"] for page in proposals])
    old_reviews = file_store.read_json("reviews.json", [])
    old_cache = file_store.read_json("ingest-cache.json", {"entries": {}})
    media_snapshots = _copy_staged_media(file_store, wiki_store, job_id, result.get("media_files", []))
    try:
        committed = wiki_store.commit_pages(proposals)
        files_written = [f"wiki/{path}" for path in committed]
        selected_paths = {f"wiki/{page['path']}" for page in proposals} | {page["path"] for page in proposals}
        selected_reviews = [review for review in result.get("reviews", []) if not review.get("affectedPages") or selected_paths.intersection(review.get("affectedPages", []))]
        if selected_reviews:
            file_store.add_reviews(selected_reviews)
        file_store.save_ingest_cache_hash(
            job["filename"], result["source_hash"], files_written,
            result.get("pipeline_version", PIPELINE_VERSION),
        )
    except BaseException:
        wiki_store.restore_pages(page_snapshots)
        file_store.write_json("reviews.json", old_reviews)
        file_store.write_json("ingest-cache.json", old_cache)
        _restore_media(media_snapshots)
        raise
    result = {
        key: value for key, value in {**result, "files_written": files_written, "status": "accepted", "accepted_page_count": len(proposals)}.items()
        if key not in {"proposals", "source_hash", "media_files"}
    }
    job_dir = file_store.data_dir / "ingest-jobs" / job_id
    (job_dir / "source.bin").unlink(missing_ok=True)
    shutil.rmtree(job_dir / "stage", ignore_errors=True)
    updated = file_store.update_ingest_job(job_id, status="accepted", step="done", message="摄入已接受并写入 Wiki", result=result)
    return {"success": True, "data": _public_job(updated or {})}


@router.post("/jobs/{job_id}/reject")
async def reject_job(job_id: str, file_store: FileStore = Depends(get_project_file_store)):
    job = file_store.get_ingest_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="摄入任务不存在")
    if job.get("status") != "awaiting_review":
        raise HTTPException(status_code=409, detail="任务不在待审核状态")
    job_dir = file_store.data_dir / "ingest-jobs" / job_id
    (job_dir / "source.bin").unlink(missing_ok=True)
    shutil.rmtree(job_dir / "stage", ignore_errors=True)
    updated = file_store.update_ingest_job(
        job_id, status="rejected", step="done", message="已拒绝，未修改 Wiki", result=None,
    )
    return {"success": True, "data": _public_job(updated or {})}


@router.post("/batch")
async def ingest_batch(
    files: list[UploadFile] = File(...),
    global_store: FileStore = Depends(get_global_store),
    file_store: FileStore = Depends(get_project_file_store),
    wiki_store: WikiStore = Depends(get_project_wiki_store),
):
    results = []
    for file in files:
        if not file.filename:
            continue
        try:
            content = await _read_upload(file)
            job = file_store.create_ingest_job(file.filename, content)
            result = await run_ingest_pipeline(
                file.filename, content, file_store, wiki_store, global_store,
                auto_commit=False, stage_dir=file_store.data_dir / "ingest-jobs" / job["id"] / "stage",
            )
            updated = file_store.update_ingest_job(job["id"], status="awaiting_review", result=result, progress=1, step="review")
            results.append({"filename": file.filename, "job": _public_job(updated or {})})
        except Exception as exc:
            results.append({"filename": file.filename, "error": str(exc)})
    return {"success": True, "data": results}
