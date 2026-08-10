"""对话 API。"""
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List

from ..dependencies import get_active_file_store, get_active_wiki_store, get_current_user
from ..storage import FileStore, WikiStore
from ..agents.chat_agent import ChatAgent

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    history: Optional[List[dict]] = []


@router.post("/api/chat")
async def chat_endpoint(
    req: ChatRequest,
    user_id: str = Depends(get_current_user),
    file_store: FileStore = Depends(get_active_file_store),
    wiki_store: WikiStore = Depends(get_active_wiki_store),
):
    """SSE 流式对话端点。"""
    # 创建或获取对话
    if req.conversation_id:
        conv = file_store.get_conversation(req.conversation_id)
        if not conv:
            conv = file_store.create_conversation(title=req.message[:50])
    else:
        conv = file_store.create_conversation(title=req.message[:50])

    conversation_id = conv["id"]

    # 获取历史消息
    history = file_store.get_messages(conversation_id)

    agent = ChatAgent(file_store, wiki_store)

    async def event_stream():
        async for event in agent.chat_stream(req.message, conversation_id, history):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/api/conversations")
async def list_conversations(file_store: FileStore = Depends(get_active_file_store)):
    """对话列表。"""
    conversations = file_store.list_conversations()
    return {"success": True, "data": conversations}


@router.get("/api/conversations/{conv_id}")
async def get_conversation(conv_id: str, file_store: FileStore = Depends(get_active_file_store)):
    """对话详情 + 消息。"""
    conv = file_store.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    messages = file_store.get_messages(conv_id)
    return {"success": True, "data": {**conv, "messages": messages}}


@router.patch("/api/conversations/{conv_id}")
async def update_conversation(conv_id: str, title: str, file_store: FileStore = Depends(get_active_file_store)):
    """重命名对话。"""
    conv = file_store.update_conversation(conv_id, title=title)
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    return {"success": True, "data": conv}


@router.delete("/api/conversations/{conv_id}")
async def delete_conversation(conv_id: str, file_store: FileStore = Depends(get_active_file_store)):
    """删除对话。"""
    if not file_store.delete_conversation(conv_id):
        raise HTTPException(status_code=404, detail="对话不存在")
    return {"success": True}
