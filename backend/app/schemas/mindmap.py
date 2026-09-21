from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime

class MindMapNode(BaseModel):
    id: str
    label: str
    type: str
    description: Optional[str] = None

class MindMapEdge(BaseModel):
    source: str
    target: str
    relationship: Optional[str] = None

class MindMapCreate(BaseModel):
    source_type: str  # "syllabus" or "note"
    source_id: int

class MindMapResponse(BaseModel):
    id: int
    user_id: int
    source_type: str
    source_id: int
    title: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
