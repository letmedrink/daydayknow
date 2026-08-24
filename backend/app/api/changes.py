"""Persistent review-before-commit jobs for chat backfill and Wiki lint."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..dependencies import get_global_store, get_project_file_store, get_project_wiki_store
from ..storage import FileStore, ProjectSchemaStore, SourceStore, WikiStore
from ..storage.wiki_store import StalePageError
from ..wiki.change_pipeline import generate_lint_change, generate_query_change

router = APIRouter(prefix="/api/projects/{project_id}")


class QueryChangeRequest(BaseModel):
    conversation_id: str
    message_id: str
    instructions: str = ""


class ProposalInput(BaseModel):
    path: str
    content: str


class AcceptChangeRequest(BaseModel):
    proposals: list[ProposalInput] | None = None


async def _run_job(job: dict, file_store: FileStore, wiki_store: WikiStore, global_store: FileStore) -> dict:
    file_store.update_change_job(job["id"], status="running", step="generate", progress=0.2)
    schema_store = ProjectSchemaStore(file_store.data_dir)
    source_store = SourceStore(file_store.data_dir)
    try:
        if job["kind"] == "query":
            origin = job.get("origin") or {}
            result = await generate_query_change(
                origin.get("question", ""), origin.get("answer", ""), origin.get("referencePaths", []),
                global_store, wiki_store, schema_store, source_store, origin.get("instructions", ""),
            )
        else:
            result = await generate_lint_change(global_store, wiki_store, schema_store, source_store)
            file_store.reset_accepted_change_count()
        return file_store.update_change_job(
            job["id"], status="awaiting_review", step="review", progress=1,
            message="请预览后接受或拒绝", result=result,
        ) or job
    except asyncio.CancelledError:
        file_store.update_change_job(job["id"], status="cancelled", step="cancelled", message="任务已取消")
        raise
    except Exception as exc:
        file_store.update_change_job(job["id"], status="failed", step="error", message=str(exc))
        raise


def maybe_schedule_auto_lint(file_store: FileStore, wiki_store: WikiStore, global_store: FileStore) -> None:
    count = file_store.record_accepted_change()
    interval = int(ProjectSchemaStore(file_store.data_dir).get()["config"].get("lint", {}).get("autoEveryAcceptedChanges", 0))
    if interval <= 0 or count < interval:
        return
    if any(job.get("kind") == "lint" and job.get("status") in {"pending", "running", "awaiting_review"} for job in file_store.list_change_jobs()):
        return
    job = file_store.create_change_job("lint", "自动 Wiki Lint", {"automatic": True})
    asyncio.create_task(_run_job(job, file_store, wiki_store, global_store))


@router.post("/changes/query")
async def create_query_change(
    request: QueryChangeRequest,
    global_store: FileStore = Depends(get_global_store),
    file_store: FileStore = Depends(get_project_file_store),
    wiki_store: WikiStore = Depends(get_project_wiki_store),
):
    if not file_store.get_conversation(request.conversation_id):
        raise HTTPException(status_code=404, detail="对话不存在")
    messages = file_store.get_messages(request.conversation_id)
    index = next((i for i, item in enumerate(messages) if item.get("id") == request.message_id), -1)
    if index < 0 or messages[index].get("role") != "assistant":
        raise HTTPException(status_code=404, detail="助手消息不存在")
    assistant = messages[index]
    question = next((item.get("content", "") for item in reversed(messages[:index]) if item.get("role") == "user"), "")
    reference_paths = [str(item.get("path")) for item in assistant.get("references", []) if item.get("path")]
    origin = {
        "conversationId": request.conversation_id,
        "messageId": request.message_id,
        "question": question,
        "answer": assistant.get("content", ""),
        "referencePaths": reference_paths,
        "instructions": request.instructions.strip(),
    }
    job = file_store.create_change_job("query", question[:80] or "问答回写", origin)
    try:
        updated = await _run_job(job, file_store, wiki_store, global_store)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"success": True, "data": updated}


@router.post("/lint")
async def create_lint_job(
    global_store: FileStore = Depends(get_global_store),
    file_store: FileStore = Depends(get_project_file_store),
    wiki_store: WikiStore = Depends(get_project_wiki_store),
):
    job = file_store.create_change_job("lint", "Wiki Lint", {"automatic": False})
    try:
        updated = await _run_job(job, file_store, wiki_store, global_store)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"success": True, "data": updated}


@router.get("/changes/jobs")
async def list_change_jobs(file_store: FileStore = Depends(get_project_file_store)):
    return {"success": True, "data": file_store.list_change_jobs()}


@router.get("/changes/jobs/{job_id}")
async def get_change_job(job_id: str, file_store: FileStore = Depends(get_project_file_store)):
    job = file_store.get_change_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="变更任务不存在")
    return {"success": True, "data": job}


@router.post("/changes/jobs/{job_id}/retry")
async def retry_change_job(
    job_id: str,
    global_store: FileStore = Depends(get_global_store),
    file_store: FileStore = Depends(get_project_file_store),
    wiki_store: WikiStore = Depends(get_project_wiki_store),
):
    job = file_store.get_change_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="变更任务不存在")
    if job.get("status") not in {"failed", "cancelled", "interrupted"}:
        raise HTTPException(status_code=409, detail="当前任务状态不可重试")
    try:
        updated = await _run_job(job, file_store, wiki_store, global_store)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"success": True, "data": updated}


@router.post("/changes/jobs/{job_id}/accept")
async def accept_change_job(
    job_id: str,
    request: AcceptChangeRequest | None = None,
    global_store: FileStore = Depends(get_global_store),
    file_store: FileStore = Depends(get_project_file_store),
    wiki_store: WikiStore = Depends(get_project_wiki_store),
):
    job = file_store.get_change_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="变更任务不存在")
    if job.get("status") != "awaiting_review":
        raise HTTPException(status_code=409, detail="任务不在待审核状态")
    result = job.get("result") or {}
    proposals = result.get("proposals", [])
    if request and request.proposals is not None:
        allowed = {page["path"]: page for page in proposals}
        proposals = []
        for submitted in request.proposals:
            if submitted.path not in allowed:
                raise HTTPException(status_code=400, detail=f"页面不属于该任务: {submitted.path}")
            proposals.append({**allowed[submitted.path], "content": submitted.content})
    if not proposals:
        raise HTTPException(status_code=400, detail="任务没有可接受的页面提案")
    snapshots = wiki_store.snapshot_pages(list(dict.fromkeys([page["path"] for page in proposals] + ["index.md", "log.md"])))
    old_reviews = file_store.read_json("reviews.json", [])
    try:
        committed = wiki_store.commit_pages(proposals)
        wiki_store.rebuild_index_page()
        wiki_store.append_log(job["kind"], job.get("title") or "Wiki 变更")
        if result.get("reviews"):
            file_store.add_reviews(result["reviews"])
    except StalePageError as exc:
        wiki_store.restore_pages(snapshots)
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except BaseException:
        wiki_store.restore_pages(snapshots)
        file_store.write_json("reviews.json", old_reviews)
        raise
    accepted = {**result, "proposals": [], "files_written": [f"wiki/{path}" for path in committed], "status": "accepted"}
    updated = file_store.update_change_job(job_id, status="accepted", step="done", message="变更已写入 Wiki", result=accepted)
    if job["kind"] != "lint":
        maybe_schedule_auto_lint(file_store, wiki_store, global_store)
    return {"success": True, "data": updated}


@router.post("/changes/jobs/{job_id}/reject")
async def reject_change_job(job_id: str, file_store: FileStore = Depends(get_project_file_store)):
    job = file_store.get_change_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="变更任务不存在")
    if job.get("status") != "awaiting_review":
        raise HTTPException(status_code=409, detail="任务不在待审核状态")
    updated = file_store.update_change_job(job_id, status="rejected", step="done", message="已拒绝，Wiki 未发生变化", result=None)
    return {"success": True, "data": updated}


@router.delete("/changes/jobs/{job_id}")
async def delete_change_job(job_id: str, file_store: FileStore = Depends(get_project_file_store)):
    try:
        deleted = file_store.delete_change_job(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="变更任务不存在")
    return {"success": True}
