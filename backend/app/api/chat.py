"""对话 API。"""
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from ..dependencies import get_global_store, get_project_file_store, get_project_wiki_store
from ..storage import FileStore, WikiStore
from ..agents.chat_agent import ChatAgent

router = APIRouter(prefix="/api/projects/{project_id}")


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


@router.post("/chat")
async def chat_endpoint(
    req: ChatRequest,
    global_store: FileStore = Depends(get_global_store),
    file_store: FileStore = Depends(get_project_file_store),
    wiki_store: WikiStore = Depends(get_project_wiki_store),
):
    """SSE 流式对话端点。"""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    # Existing conversations must resolve inside the active project. New ones are
    # only indexed after a complete upstream response has been persisted.
    if req.conversation_id:
        conv = file_store.get_conversation(req.conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="对话不存在")
        conversation_id = conv["id"]
        history = file_store.get_messages(conversation_id)
    else:
        conversation_id = file_store.new_conversation_id()
        history = []

    agent = ChatAgent(global_store, file_store, wiki_store)

    async def event_stream():
        assistant_message_id = None
        try:
            async for event in agent.chat_stream(req.message, conversation_id, history):
                if event["type"] == "_complete":
                    saved = file_store.save_turn(
                        conversation_id,
                        req.message[:50],
                        {"role": "user", "content": req.message},
                        {
                            "role": "assistant",
                            "content": event["assistant_content"],
                            "references": event["references"],
                            "options": event["options"],
                        },
                    )
                    assistant_message_id = saved["messages"][-1]["id"]
                    continue
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id, 'message_id': assistant_message_id})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'error': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/conversations")
async def list_conversations(file_store: FileStore = Depends(get_project_file_store)):
    """对话列表。"""
    conversations = file_store.list_conversations()
    return {"success": True, "data": conversations}


@router.get("/conversations/{conv_id}")
async def get_conversation(conv_id: str, file_store: FileStore = Depends(get_project_file_store)):
    """对话详情 + 消息。"""
    conv = file_store.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    messages = file_store.get_messages(conv_id)
    return {"success": True, "data": {**conv, "messages": messages}}


@router.patch("/conversations/{conv_id}")
async def update_conversation(conv_id: str, title: str, file_store: FileStore = Depends(get_project_file_store)):
    """重命名对话。"""
    conv = file_store.update_conversation(conv_id, title=title)
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    return {"success": True, "data": conv}


@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str, file_store: FileStore = Depends(get_project_file_store)):
    """删除对话。"""
    if not file_store.delete_conversation(conv_id):
        raise HTTPException(status_code=404, detail="对话不存在")
    return {"success": True}
