from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime

# 通用响应模型
class ErrorResponse(BaseModel):
    error: str

class SuccessResponse(BaseModel):
    message: str

# 用户身份依赖
class UserIdRequest(BaseModel):
    user_id: Optional[str] = None

# 术语相关模型
class Term(BaseModel):
    id: str
    user_id: str
    term: str
    original_context: str
    domain: str
    confidence: float
    processed_status: str = "pending"
    captured_at: datetime

class TermCreate(BaseModel):
    raw_text: str

class TermResponse(BaseModel):
    extracted_term: str
    all_terms: List[str]
    domain: str
    message: str
    user_id: str
    saved_count: int

# 日报相关模型
class DailyDocCard(BaseModel):
    term_id: str
    term: str
    context: str
    simple: str
    deep: str
    case: str
    history: str
    related: List[str]
    controversy: str
    source: str

class DailyDoc(BaseModel):
    id: str
    user_id: str
    doc_date: str
    cards: List[DailyDocCard]
    term_count: int
    generated_at: datetime

class DailyDocResponse(BaseModel):
    doc_date: str
    title: str
    cards: List[DailyDocCard]
    new_connections: List[dict]
    generated_at: datetime

class DailyDocNotFoundResponse(BaseModel):
    doc_date: str
    title: str
    cards: List[DailyDocCard]
    new_connections: List[dict]
    message: str
    terms_collected: List[dict]
    terms_count: int
    can_generate: bool

class DailyDocGenerateRequest(BaseModel):
    date: Optional[str] = None

class DailyDocGenerateResponse(BaseModel):
    message: str
    doc_date: str
    term_count: Optional[int] = None
    generated_at: Optional[datetime] = None
    already_exists: Optional[bool] = None

# 批处理相关模型
class BatchRequest(BaseModel):
    userId: Optional[str] = None
    date: Optional[str] = None

class BatchResponse(BaseModel):
    message: str
    processed: int
    skipped: int
    timestamp: datetime

class BatchHealthResponse(BaseModel):
    message: str
    usage: str
    timestamp: datetime

# 星图相关模型
class StarNode(BaseModel):
    id: str
    user_id: str
    term_id: str
    term_name: str
    domain: str
    x: float
    y: float
    confirmed_at: datetime

class StarEdge(BaseModel):
    id: str
    user_id: str
    from_node_id: str
    to_node_id: str
    relation_type: str
    description: str
    discovered_at: datetime

class StarMapResponse(BaseModel):
    nodes: List[StarNode]
    edges: List[StarEdge]
    stats: dict

# 术语确认相关模型
class TermConfirmResponse(BaseModel):
    message: str
    star_node_id: str
    new_connections: List[dict]
    term_name: str
    domain: str

# 任务相关模型
class TaskResponse(BaseModel):
    task_id: str
    status: str
    progress: int = 0
    total: int = 0
    current_step: str = ""
    percent: int = 0
    result: Optional[Any] = None
    error: Optional[str] = None

class AsyncTaskResponse(BaseModel):
    message: str
    task_id: str
    status_url: str