"""API 响应模型 — 统一响应格式。"""
from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class NodeResponse(BaseModel):
    id: str
    user_id: str
    name: str
    domain: Optional[str] = None
    description: Optional[str] = None
    confidence: float = 0.8
    source_type: str = "conversation"
    source_ref: Optional[str] = None
    current_version: int = 1
    created_at: str


class EdgeResponse(BaseModel):
    id: str
    user_id: str
    from_node_id: str
    to_node_id: str
    relation_type: str
    strength: float = 1.0
    description: Optional[str] = None
    source_ref: Optional[str] = None
    created_at: str


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    sequence_number: Optional[int] = None
    created_at: str


class ConversationResponse(BaseModel):
    id: str
    user_id: str
    title: Optional[str] = None
    status: str = "active"
    message_count: int = 0
    created_at: str
    updated_at: str


class ConversationDetailResponse(ConversationResponse):
    messages: List[MessageResponse] = []


class ApiResponse(BaseModel):
    """通用 API 响应包装。"""
    success: bool = True
    data: Any = None
    error: Optional[str] = None


class PaginatedResponse(BaseModel):
    """分页响应。"""
    items: List[Any] = []
    total: int = 0
    limit: int = 50
    offset: int = 0


class StatsResponse(BaseModel):
    total_nodes: int
    total_edges: int
    total_conversations: int
    domains: dict
    top_connected_nodes: List[dict]


class HealthResponse(BaseModel):
    status: str
    mock_mode: bool
    checks: dict
