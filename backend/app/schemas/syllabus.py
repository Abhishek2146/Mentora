"""
Syllabus schemas
"""
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field, computed_field


class SyllabusStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PARSED = "parsed"
    FAILED = "failed"
    RAG_READY = "rag_ready"
    EMBEDDING_FAILED = "embedding_failed"


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


class ChapterOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    topics: Optional[Any] = None
    order: int
    subject_id: int
    estimated_hours: int = 0

    class Config:
        from_attributes = True


class SubjectOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    order: int

    class Config:
        from_attributes = True


class SubjectWithChapters(SubjectOut):
    chapters: List[ChapterOut] = []


class UnitOut(BaseModel):
    """Frontend-compatible representation of a subject/unit."""

    unitNumber: int
    title: str
    description: Optional[str] = None
    estimatedHours: int = 0
    topics: Optional[List[str]] = None


class SyllabusOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    file_path: Optional[str] = None
    file_type: Optional[str] = None
    status: SyllabusStatus
    is_ai_processed: bool = False
    parsed_data: Optional[Any] = None
    subjects: List[SubjectWithChapters] = []

    class Config:
        from_attributes = True

    @computed_field
    @property
    def subject(self) -> str:
        return self.title

    @computed_field
    @property
    def units(self) -> List[UnitOut]:
        """Frontend units: one entry per CHAPTER (a real syllabus unit).

        Chapters are exactly what the parser extracted as numbered
        units/modules from the uploaded document - generic section
        headings ("Syllabus", "Objectives", ...) never become chapters,
        so they never appear as units here either.  Unit numbers are a
        global running index in document order; hours come from the
        source only (0 when the unit does not state any).
        """
        result: List[UnitOut] = []
        unit_number = 0
        for s in self.subjects:
            for chap in s.chapters:
                unit_number += 1

                topics: List[str] = []
                if chap.topics:
                    if isinstance(chap.topics, list):
                        topics.extend(str(t) for t in chap.topics)
                    elif isinstance(chap.topics, dict):
                        topics.extend(str(v) for v in chap.topics.values())

                result.append(
                    UnitOut(
                        unitNumber=unit_number,
                        title=chap.name,
                        description=chap.description,
                        estimatedHours=chap.estimated_hours or 0,
                        topics=topics if topics else None,
                    )
                )
        return result

    @computed_field
    @property
    def totalTopics(self) -> int:
        total = 0
        for subj in self.subjects:
            for chap in subj.chapters:
                if chap.topics:
                    if isinstance(chap.topics, list):
                        total += len(chap.topics)
                    elif isinstance(chap.topics, dict):
                        total += len(chap.topics)
        return total

    @computed_field
    @property
    def estimatedHours(self) -> int:
        total = 0
        for subj in self.subjects:
            for chap in subj.chapters:
                if chap.estimated_hours:
                    total += chap.estimated_hours
        return total
