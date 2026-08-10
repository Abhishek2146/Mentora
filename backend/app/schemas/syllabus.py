"""
Syllabus schemas
"""
from enum import Enum
from typing import Optional, List, Any

from pydantic import BaseModel, Field


class SyllabusStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PARSED = "parsed"
    FAILED = "failed"


class SyllabusBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None


class SyllabusCreate(SyllabusBase):
    file_path: Optional[str] = None
    file_type: Optional[str] = None


class SyllabusUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[SyllabusStatus] = None


class SubjectOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    order: int

    class Config:
        from_attributes = True


class ChapterOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    order: int
    subject_id: int

    class Config:
        from_attributes = True


class SubjectWithChapters(SubjectOut):
    chapters: List[ChapterOut] = []


class SyllabusOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    file_path: Optional[str] = None
    file_type: Optional[str] = None
    status: SyllabusStatus
    parsed_data: Optional[Any] = None
    subjects: List[SubjectWithChapters] = []

    class Config:
        from_attributes = True
