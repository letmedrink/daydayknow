from pydantic import BaseModel
from typing import List, Optional


class KgNode(BaseModel):
    id: str
    user_id: str
    name: str
    domain: Optional[str] = None
    description: Optional[str] = None
    confidence: float = 0.8
    source_type: str = "conversation"
    source_ref: Optional[str] = None
    created_at: Optional[str] = None


class KgEdge(BaseModel):
    id: str
    user_id: str
    from_node_id: str
    to_node_id: str
    relation_type: str
    strength: float = 1.0
    description: Optional[str] = None
    source_ref: Optional[str] = None
    created_at: Optional[str] = None


class ExtractionResult(BaseModel):
    nodes: List[dict]
    edges: List[dict]
