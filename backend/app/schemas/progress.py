"""
Progress schemas
"""
from typing import Optional, List, Any
from datetime import date

from pydantic import BaseModel, Field


class ProgressBase(BaseModel):
    progress_type: str = Field(..., max_length=50)
    value: float = 0.0
    target_value: float = 100.0
    syllabus_id: Optional[int] = None
    subject_id: Optional[int] = None
    chapter_id: Optional[int] = None
    metadata: Optional[Any] = None


class ProgressCreate(ProgressBase):
    pass


class ProgressUpdate(BaseModel):
    value: Optional[float] = None
    metadata: Optional[Any] = None


class ProgressOut(ProgressBase):
    id: int
    user_id: int
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class WeakTopicBase(BaseModel):
    topic_name: str = Field(..., max_length=255)
    syllabus_id: Optional[int] = None
    subject_id: Optional[int] = None
    chapter_id: Optional[int] = None
    accuracy: float = 0.0
    confidence_level: float = 0.0
    total_attempts: int = 0
    last_attempted: Optional[date] = None
    recommended_action: Optional[str] = None


class WeakTopicOut(WeakTopicBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True
