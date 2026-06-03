"""API 响应模型。"""
from pydantic import BaseModel
from typing import Optional, List, Any


class ApiResponse(BaseModel):
    success: bool = True
    data: Any = None
    error: Optional[str] = None


class PaginatedResponse(BaseModel):
    items: List[Any] = []
    total: int = 0
    limit: int = 50
    offset: int = 0


class HealthResponse(BaseModel):
    status: str
    checks: dict


class WikiPageResponse(BaseModel):
    name: str
    path: str
    type: str
    title: str


class WikiGraphNode(BaseModel):
    id: str
    title: str
    type: str
    tags: List[str] = []
    path: str


class WikiGraphEdge(BaseModel):
    source: str
    target: str
    type: str = "wikilink"


class WikiGraphResponse(BaseModel):
    nodes: List[WikiGraphNode]
    edges: List[WikiGraphEdge]
    communities: List[dict] = []


class SearchResult(BaseModel):
    name: str
    path: str
    type: str
    title: str
    score: int
    snippet: str


class ReviewItem(BaseModel):
    id: str
    type: str  # contradiction | duplicate | missing-page | suggestion
    title: str
    description: str
    sourcePath: Optional[str] = None
    affectedPages: List[str] = []
    searchQueries: List[str] = []
    options: List[dict] = []
    resolved: bool = False
    resolvedAction: Optional[str] = None
    createdAt: int


class IngestProgressEvent(BaseModel):
    step: str
    progress: float
    message: str
    files_written: List[str] = []
