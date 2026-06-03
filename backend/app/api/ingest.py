"""文档摄入 API。"""
import asyncio
import json
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse

from ..dependencies import get_file_store, get_wiki_store
from ..storage import FileStore, WikiStore

router = APIRouter(prefix="/api/ingest")


@router.post("")
async def ingest_file(
    file: UploadFile = File(...),
    file_store: FileStore = Depends(get_file_store),
    wiki_store: WikiStore = Depends(get_wiki_store),
):
    """上传文件，触发摄入流程（SSE 实时返回进度）。"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名为空")

    content = await file.read()

    # 用 asyncio.Queue 实现实时事件传递
    queue: asyncio.Queue = asyncio.Queue()

    async def on_progress(step, progress, message):
        await queue.put({"type": "progress", "step": step, "progress": progress, "message": message})

    async def run_pipeline():
        from ..ingest.pipeline import run_ingest_pipeline
        try:
            result = await run_ingest_pipeline(
                file.filename, content, file_store, wiki_store,
                progress_callback=on_progress,
            )
            await queue.put({"type": "done", "result": result})
        except Exception as e:
            await queue.put({"type": "error", "error": str(e)})
        finally:
            await queue.put(None)  # 结束信号

    # 后台启动 pipeline
    task = asyncio.create_task(run_pipeline())

    async def event_stream():
        while True:
            evt = await queue.get()
            if evt is None:
                break
            yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/batch")
async def ingest_batch(
    files: list[UploadFile] = File(...),
    file_store: FileStore = Depends(get_file_store),
    wiki_store: WikiStore = Depends(get_wiki_store),
):
    """批量文件摄入。"""
    from ..ingest.pipeline import run_ingest_pipeline

    results = []
    for file in files:
        if not file.filename:
            continue
        content = await file.read()
        try:
            result = await run_ingest_pipeline(
                file.filename, content, file_store, wiki_store,
            )
            results.append({"filename": file.filename, **result})
        except Exception as e:
            results.append({"filename": file.filename, "error": str(e)})

    return {"success": True, "data": results}
