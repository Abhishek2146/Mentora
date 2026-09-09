"""
Note schemas
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class NoteBase(BaseModel):
    title: str = Field(..., max_length=255)
    content: str = Field(default="")
    syllabus_id: Optional[int] = None


class NoteCreate(NoteBase):
    pass


class NoteUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = None
    syllabus_id: Optional[int] = None
    ai_summary: Optional[str] = None


class SyllabusNoteGenerateRequest(BaseModel):
    syllabus_id: int
    topic_focus: Optional[str] = None


class NoteOut(NoteBase):
    id: int
    user_id: int
    ai_summary: Optional[str] = None
    summary_generated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NoteSummaryOut(BaseModel):
    note_id: int
    ai_summary: str
    summary_generated_at: Optional[datetime] = None
