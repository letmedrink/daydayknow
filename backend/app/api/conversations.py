from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional

from .chat import graph_store
from ..dependencies import get_current_user

router = APIRouter()


class RenameRequest(BaseModel):
    title: str


class BulkDeleteRequest(BaseModel):
    conversation_ids: List[str]


@router.get("/api/conversations")
async def list_conversations(
    user_id: str = Depends(get_current_user),
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """列出当前用户的对话。支持 q 参数搜索标题。"""
    if q:
        return await graph_store.search_conversations(user_id, q, limit=limit)
    return await graph_store.list_conversations(user_id, limit=limit, offset=offset)


@router.get("/api/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    limit: Optional[int] = None,
    offset: int = 0,
    user_id: str = Depends(get_current_user),
):
    """获取对话详情及消息。支持 limit/offset 消息分页。"""
    conv = await graph_store.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = await graph_store.get_messages(conversation_id, limit=limit, offset=offset)
    return {**conv, "messages": messages}


@router.delete("/api/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user_id: str = Depends(get_current_user),
):
    """删除对话及消息。"""
    deleted = await graph_store.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"deleted": True}


@router.patch("/api/conversations/{conversation_id}")
async def rename_conversation(
    conversation_id: str,
    req: RenameRequest,
    user_id: str = Depends(get_current_user),
):
    """重命名对话。"""
    if not req.title.strip():
        raise HTTPException(status_code=400, detail="标题不能为空")
    conv = await graph_store.rename_conversation(conversation_id, req.title.strip())
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.post("/api/conversations/bulk-delete")
async def bulk_delete_conversations(
    req: BulkDeleteRequest,
    user_id: str = Depends(get_current_user),
):
    """批量删除对话。"""
    if not req.conversation_ids:
        return {"deleted": 0}
    count = await graph_store.delete_conversations_bulk(user_id, req.conversation_ids)
    return {"deleted": count}


@router.get("/api/conversations/{conversation_id}/summaries")
async def get_conversation_summaries(
    conversation_id: str,
    user_id: str = Depends(get_current_user),
):
    """获取对话的所有摘要。"""
    conv = await graph_store.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    summaries = await graph_store.get_summaries(conversation_id)
    return {"summaries": summaries}


@router.get("/api/conversations/{conversation_id}/search")
async def search_messages(
    conversation_id: str,
    q: str,
    limit: int = 20,
    user_id: str = Depends(get_current_user),
):
    """搜索对话消息内容。"""
    conv = await graph_store.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = await graph_store.search_messages(conversation_id, q, limit=limit)
    return {"messages": messages, "query": q}


@router.get("/api/conversations/{conversation_id}/export")
async def export_conversation(
    conversation_id: str,
    format: str = "markdown",
    user_id: str = Depends(get_current_user),
):
    """导出对话。

    format=markdown: 返回 Markdown 格式文本
    format=json: 返回 JSON 格式
    """
    conv = await graph_store.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = await graph_store.get_messages(conversation_id)

    if format == "json":
        return JSONResponse({
            "conversation": conv,
            "messages": messages,
        })

    # Markdown 格式
    title = conv.get("title") or "未命名对话"
    lines = [f"# {title}\n"]
    lines.append(f"创建时间: {conv.get('created_at', 'N/A')}\n")
    lines.append("---\n")

    for msg in messages:
        role = "**用户**" if msg["role"] == "user" else "**助手**"
        lines.append(f"\n{role}\n\n{msg['content']}\n")

    md_text = "\n".join(lines)
    return PlainTextResponse(
        md_text,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="conversation-{conversation_id[:8]}.md"'},
    )
