"""深度研究 API。"""
import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from ..dependencies import get_global_store, get_project_file_store, get_project_wiki_store
from ..storage import FileStore, WikiStore

router = APIRouter(prefix="/api/projects/{project_id}/research")


class ResearchRequest(BaseModel):
    topic: str
    keywords: Optional[list[str]] = None


@router.post("")
async def deep_research(
    req: ResearchRequest,
    global_store: FileStore = Depends(get_global_store),
    file_store: FileStore = Depends(get_project_file_store),
    wiki_store: WikiStore = Depends(get_project_wiki_store),
):
    """触发 Deep Research（SSE 实时返回进度）。"""
    if not req.topic.strip():
        raise HTTPException(status_code=400, detail="研究主题不能为空")

    queue: asyncio.Queue = asyncio.Queue()

    async def on_progress(step, progress, message):
        await queue.put({"type": "progress", "step": step, "progress": progress, "message": message})

    async def run_task():
        from ..research.deep_research import run_deep_research
        try:
            result = await run_deep_research(
                req.topic, file_store, wiki_store, global_store,
                search_queries=req.keywords,
                progress_callback=on_progress,
            )
            await queue.put({"type": "done", "result": result})
        except Exception as e:
            await queue.put({"type": "error", "error": str(e)})
        finally:
            await queue.put(None)

    asyncio.create_task(run_task())

    async def event_stream():
        while True:
            evt = await queue.get()
            if evt is None:
                break
            yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
