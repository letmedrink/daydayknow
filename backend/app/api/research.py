"""Persistent, review-before-commit Deep Research API."""

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..dependencies import get_global_store, get_project_file_store, get_project_wiki_store
from ..research.deep_research import run_deep_research
from ..storage import FileStore, WikiStore

router = APIRouter(prefix="/api/projects/{project_id}/research")
_RUNNING: dict[str, asyncio.Task] = {}


class ResearchRequest(BaseModel):
    topic: str
    keywords: Optional[list[str]] = None
    review_id: Optional[str] = None


def _key(store: FileStore, job_id: str) -> str:
    return f"{store.data_dir.resolve()}::{job_id}"


def _start_job(job: dict, file_store: FileStore, wiki_store: WikiStore, global_store: FileStore):
    queue: asyncio.Queue = asyncio.Queue()
    job_id = job["id"]

    async def progress(step, value, message):
        file_store.update_research_job(job_id, status="running", step=step, progress=value, message=message)
        await queue.put({"type": "progress", "job_id": job_id, "step": step, "progress": value, "message": message})

    async def run():
        try:
            file_store.update_research_job(job_id, status="running", step="queries", progress=0)
            result = await run_deep_research(
                job["topic"], file_store, wiki_store, global_store,
                search_queries=job.get("keywords") or None,
                progress_callback=progress,
                auto_commit=False,
            )
            updated = file_store.update_research_job(
                job_id, status="awaiting_review", step="review", progress=1,
                message="研究完成，请审核来源和页面", result=result,
            )
            if job.get("reviewId"):
                file_store.update_review(job["reviewId"], status="awaiting_review", resultJobId=job_id)
            await queue.put({"type": "done", "job": updated, "result": result})
        except asyncio.CancelledError:
            file_store.update_research_job(job_id, status="cancelled", step="cancelled", message="研究已取消")
            if job.get("reviewId"):
                file_store.update_review(job["reviewId"], status="pending", error=None)
            await queue.put({"type": "error", "error": "研究已取消", "code": "cancelled"})
        except Exception as exc:
            file_store.update_research_job(job_id, status="failed", step="error", message=str(exc))
            if job.get("reviewId"):
                file_store.update_review(job["reviewId"], status="pending", error=str(exc))
            await queue.put({"type": "error", "error": str(exc), "code": "research_failed"})
        finally:
            _RUNNING.pop(_key(file_store, job_id), None)
            await queue.put(None)

    task = asyncio.create_task(run())
    _RUNNING[_key(file_store, job_id)] = task
    return task, queue


def _stream(task: asyncio.Task, queue: asyncio.Queue, file_store: FileStore, job_id: str):
    async def events():
        finished = False
        try:
            while True:
                event = await queue.get()
                if event is None:
                    finished = True
                    break
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        finally:
            if not finished and not task.done():
                task.cancel()
                file_store.update_research_job(job_id, status="cancelled", step="cancelled", message="客户端已断开")
    return StreamingResponse(events(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"})


@router.post("")
async def deep_research(
    req: ResearchRequest,
    global_store: FileStore = Depends(get_global_store),
    file_store: FileStore = Depends(get_project_file_store),
    wiki_store: WikiStore = Depends(get_project_wiki_store),
):
    topic = req.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="研究主题不能为空")
    if req.review_id and not file_store.get_review(req.review_id):
        raise HTTPException(status_code=404, detail="关联审阅项不存在")
    job = file_store.create_research_job(topic, req.keywords or [], req.review_id)
    if req.review_id:
        file_store.update_review(req.review_id, status="processing", resultJobId=job["id"], error=None)
    task, queue = _start_job(job, file_store, wiki_store, global_store)
    return _stream(task, queue, file_store, job["id"])


@router.get("/jobs")
async def list_jobs(file_store: FileStore = Depends(get_project_file_store)):
    return {"success": True, "data": file_store.list_research_jobs()}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, file_store: FileStore = Depends(get_project_file_store)):
    job = file_store.get_research_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="研究任务不存在")
    return {"success": True, "data": job}


@router.post("/jobs/{job_id}/retry")
async def retry_job(
    job_id: str, global_store: FileStore = Depends(get_global_store),
    file_store: FileStore = Depends(get_project_file_store),
    wiki_store: WikiStore = Depends(get_project_wiki_store),
):
    job = file_store.get_research_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="研究任务不存在")
    if job.get("status") not in {"failed", "cancelled", "interrupted"}:
        raise HTTPException(status_code=409, detail="当前任务状态不可重试")
    task, queue = _start_job(job, file_store, wiki_store, global_store)
    return _stream(task, queue, file_store, job_id)


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str, file_store: FileStore = Depends(get_project_file_store)):
    job = file_store.get_research_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="研究任务不存在")
    task = _RUNNING.get(_key(file_store, job_id))
    if task and not task.done():
        task.cancel()
    updated = file_store.update_research_job(job_id, status="cancelled", step="cancelled", message="研究已取消")
    return {"success": True, "data": updated}


@router.post("/jobs/{job_id}/accept")
async def accept_job(
    job_id: str, file_store: FileStore = Depends(get_project_file_store),
    wiki_store: WikiStore = Depends(get_project_wiki_store),
):
    job = file_store.get_research_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="研究任务不存在")
    if job.get("status") != "awaiting_review":
        raise HTTPException(status_code=409, detail="研究任务不在待审核状态")
    result = job.get("result") or {}
    proposals = result.get("proposals", [])
    snapshots = wiki_store.snapshot_pages([page["path"] for page in proposals])
    old_reviews = file_store.read_json("reviews.json", [])
    try:
        committed = wiki_store.commit_pages(proposals)
        if result.get("reviews"):
            file_store.add_reviews(result["reviews"])
        if job.get("reviewId"):
            file_store.resolve_review(job["reviewId"], "deep_research")
    except BaseException:
        wiki_store.restore_pages(snapshots)
        file_store.write_json("reviews.json", old_reviews)
        raise
    accepted_result = {
        **result, "files_written": [f"wiki/{path}" for path in committed], "status": "accepted",
    }
    accepted_result.pop("proposals", None)
    updated = file_store.update_research_job(job_id, status="accepted", step="done", message="研究结果已写入 Wiki", result=accepted_result)
    return {"success": True, "data": updated}


@router.post("/jobs/{job_id}/reject")
async def reject_job(job_id: str, file_store: FileStore = Depends(get_project_file_store)):
    job = file_store.get_research_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="研究任务不存在")
    if job.get("status") != "awaiting_review":
        raise HTTPException(status_code=409, detail="研究任务不在待审核状态")
    if job.get("reviewId"):
        file_store.update_review(job["reviewId"], status="pending", resultJobId=None)
    updated = file_store.update_research_job(job_id, status="rejected", step="done", message="已拒绝，Wiki 未发生变化", result=None)
    return {"success": True, "data": updated}
