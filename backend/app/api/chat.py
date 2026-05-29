import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional

from ..agents.context import AgentContext, Message
from ..agents.chat_agent import ChatAgent, EXPERT_PROMPTS
from ..agents.router_agent import RouterAgent
from ..db.factory import get_graph_store
from ..dependencies import get_current_user
from ..models.responses import StatsResponse
from ..tasks.queue import enqueue_post_process, get_task_status
from ..utils.logger import create_module_logger

log = create_module_logger("api.chat")
router = APIRouter()

graph_store = get_graph_store()


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    history: Optional[List[dict]] = []


class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 20


class NodeUpdateRequest(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    description: Optional[str] = None
    confidence: Optional[float] = None
    reason: Optional[str] = "manual update"


class EdgeUpdateRequest(BaseModel):
    relation_type: Optional[str] = None
    strength: Optional[float] = None
    description: Optional[str] = None


class EdgeCreateRequest(BaseModel):
    from_node_id: str
    to_node_id: str
    relation_type: str
    strength: Optional[float] = 1.0
    description: Optional[str] = None


class BulkDeleteNodesRequest(BaseModel):
    node_ids: List[str]


@router.post("/api/chat")
async def chat_endpoint(
    req: ChatRequest,
    user_id: str = Depends(get_current_user),
):
    """SSE 流式对话端点。响应完成后将知识提取加入后台任务队列。"""
    # 新对话时创建记录
    if req.conversation_id:
        conversation_id = req.conversation_id
        server_messages = await graph_store.get_messages(conversation_id)
        messages = [Message(role=m["role"], content=m["content"]) for m in server_messages]
    else:
        title = req.message[:50] if req.message else None
        conv = await graph_store.create_conversation(user_id=user_id, title=title)
        conversation_id = conv["id"]
        messages = [Message(role=m["role"], content=m["content"]) for m in (req.history or [])]

    # 保存用户消息
    await graph_store.add_message(conversation_id, "user", req.message)
    messages.append(Message(role="user", content=req.message))

    context = AgentContext(
        conversation_id=conversation_id,
        user_id=user_id,
        messages=messages,
    )

    # 路由 Agent: 意图分类 + 专家匹配
    router_agent = RouterAgent()
    route_result = await router_agent.execute(context)
    routing = route_result.data if route_result.success else {"expert": "generalist", "depth": "quick"}
    context.intermediate_results["routing"] = routing

    # 注入画像到 ChatAgent
    profile = await graph_store.get_profile(user_id)
    expert = routing.get("expert", "generalist")
    system_prompt = EXPERT_PROMPTS.get(expert, EXPERT_PROMPTS["generalist"])
    chat_agent = ChatAgent(system_prompt=system_prompt, profile=profile)

    async def event_stream():
        full_response = ""
        async for chunk in chat_agent.stream(context):
            full_response += chunk
            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

        # 保存助手回复
        await graph_store.add_message(conversation_id, "assistant", full_response)

        yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id})}\n\n"

        # 后台任务：知识提取 + 画像更新
        task = await enqueue_post_process(conversation_id, user_id)

        if task["status"] == "completed" and task.get("result"):
            result = task["result"]
            yield f"data: {json.dumps({'type': 'extraction', 'nodes': result.get('nodes', []), 'edges': result.get('edges', [])})}\n\n"

            conflicts = result.get("conflicts")
            if conflicts and conflicts.get("has_conflict"):
                yield f"data: {json.dumps({'type': 'conflict', 'conflicts': conflicts['conflicts']})}\n\n"

            if result.get("profile_updated"):
                yield f"data: {json.dumps({'type': 'profile', 'updated': True})}\n\n"
        else:
            # ARQ 异步模式：通知前端任务已入队
            yield f"data: {json.dumps({'type': 'task_enqueued', 'task_id': task['task_id'], 'conversation_id': conversation_id})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/api/tasks/{task_id}")
async def get_task_result(task_id: str):
    """查询后台任务状态。"""
    status = await get_task_status(task_id)
    if status is None:
        return {"status": "not_found"}
    return status


@router.post("/api/search")
async def search_knowledge(
    req: SearchRequest,
    user_id: str = Depends(get_current_user),
):
    """搜索知识图谱节点。"""
    nodes = await graph_store.search_nodes(
        user_id=user_id,
        query=req.query,
        limit=req.limit or 20,
    )
    # 去掉内部评分字段
    for node in nodes:
        node.pop("_score", None)
    return {"nodes": nodes, "query": req.query}


@router.get("/api/stats/{user_id}", response_model=StatsResponse)
async def get_statistics(user_id: str):
    """获取用户知识图谱统计。"""
    return await graph_store.get_statistics(user_id)


@router.get("/api/knowledge/{user_id}/export")
async def export_knowledge(
    user_id: str,
    format: str = "json",
):
    """导出用户知识图谱。format=json|csv"""
    data = await graph_store.export_graph(user_id, fmt=format)

    if format == "csv":
        import csv
        import io

        # 导出为 CSV（节点和边分别拼接）
        output = io.StringIO()
        # 节点部分
        output.write("# Nodes\n")
        if data["nodes"]:
            writer = csv.DictWriter(output, fieldnames=data["nodes"][0].keys())
            writer.writeheader()
            writer.writerows(data["nodes"])
        # 边部分
        output.write("\n# Edges\n")
        if data["edges"]:
            writer = csv.DictWriter(output, fieldnames=data["edges"][0].keys())
            writer.writeheader()
            writer.writerows(data["edges"])

        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(
            output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="knowledge-{user_id[:8]}.csv"'},
        )

    return data


@router.get("/api/knowledge/{user_id}")
async def get_knowledge(user_id: str, domain: Optional[str] = None):
    """获取用户的完整知识图谱。支持 domain 参数过滤领域。"""
    nodes = await graph_store.get_user_nodes(user_id, domain=domain)
    edges = await graph_store.get_user_edges(user_id)
    return {"nodes": nodes, "edges": edges}


@router.get("/api/knowledge/{user_id}/domains")
async def get_domains(user_id: str):
    """获取用户的所有领域及节点数量。"""
    domains = await graph_store.get_user_domains(user_id)
    return {"domains": domains}


@router.get("/api/knowledge/node/{node_id}")
async def get_node_detail(node_id: str):
    """获取节点详情及其邻居。"""
    result = await graph_store.get_node_with_neighbors(node_id)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Node not found")
    return result


@router.delete("/api/knowledge/node/{node_id}")
async def delete_node(node_id: str):
    """删除节点及其关联边。"""
    deleted = await graph_store.delete_node(node_id)
    if not deleted:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Node not found")
    return {"deleted": True}


@router.post("/api/knowledge/nodes/bulk-delete")
async def bulk_delete_nodes(
    req: BulkDeleteNodesRequest,
    user_id: str = Depends(get_current_user),
):
    """批量删除节点及其关联边。"""
    if not req.node_ids:
        return {"deleted": 0}
    count = await graph_store.delete_nodes_bulk(user_id, req.node_ids)
    return {"deleted": count}


@router.patch("/api/knowledge/node/{node_id}")
async def update_node(
    node_id: str,
    req: NodeUpdateRequest,
):
    """更新节点（创建新版本，旧版本保留历史）。"""
    new_data = {}
    if req.name is not None:
        new_data["name"] = req.name
    if req.domain is not None:
        new_data["domain"] = req.domain
    if req.description is not None:
        new_data["description"] = req.description
    if req.confidence is not None:
        new_data["confidence"] = req.confidence

    if not new_data:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="至少需要一个更新字段")

    result = await graph_store.supersede_node(
        node_id=node_id,
        new_data=new_data,
        reason=req.reason or "manual update",
    )
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Node not found")
    return result


@router.get("/api/knowledge/node/{node_id}/versions")
async def get_node_versions(node_id: str):
    """获取节点版本历史。"""
    versions = await graph_store.get_node_versions(node_id)
    return {"versions": versions}


@router.delete("/api/knowledge/edge/{edge_id}")
async def delete_edge(edge_id: str):
    """删除单条边。"""
    deleted = await graph_store.delete_edge(edge_id)
    if not deleted:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Edge not found")
    return {"deleted": True}


@router.patch("/api/knowledge/edge/{edge_id}")
async def update_edge(
    edge_id: str,
    req: EdgeUpdateRequest,
):
    """更新边属性。"""
    updates = {}
    if req.relation_type is not None:
        updates["relation_type"] = req.relation_type
    if req.strength is not None:
        updates["strength"] = req.strength
    if req.description is not None:
        updates["description"] = req.description

    result = await graph_store.update_edge(edge_id, updates)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Edge not found")
    return result


@router.post("/api/knowledge/edge")
async def create_edge(
    req: EdgeCreateRequest,
    user_id: str = Depends(get_current_user),
):
    """创建节点之间的边。"""
    edge = await graph_store.create_edge(
        user_id=user_id,
        from_node_id=req.from_node_id,
        to_node_id=req.to_node_id,
        relation_type=req.relation_type,
        strength=req.strength or 1.0,
        description=req.description,
    )
    if not edge:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="无法创建边（节点不存在或边已存在）")
    return edge


@router.get("/api/profile/{user_id}")
async def get_profile(user_id: str):
    """获取用户画像。"""
    profile = await graph_store.get_profile(user_id)
    if not profile:
        return {"data": None}
    return profile
