"""
Syllabus schemas
"""
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field, ConfigDict, computed_field


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


class SyllabusSearchRequest(BaseModel):
    """Request schema for syllabus search."""
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    search_in: Optional[List[str]] = Field(
        default=None,
        description="Fields to search in: title, description, extracted_text, subjects, chapters, topics"
    )
    status: Optional[SyllabusStatus] = Field(default=None, description="Filter by status")
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")


class SyllabusSearchResult(BaseModel):
    """Search result for a syllabus."""
    id: int
    title: str
    description: Optional[str] = None
    file_type: Optional[str] = None
    status: SyllabusStatus
    is_processed: bool
    is_ai_processed: bool
    created_at: Any
    updated_at: Any
    matched_fields: List[str] = []

    model_config = ConfigDict(from_attributes=True)


class SyllabusSearchResponse(BaseModel):
    """Response for syllabus search."""
    items: List[SyllabusSearchResult]
    total: int
    page: int
    per_page: int
    pages: int
    query: str


class ChapterOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    topics: Optional[Any] = None
    order: int
    subject_id: int
    estimated_hours: int = 0

    model_config = ConfigDict(from_attributes=True)


class SubjectOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    order: int

    model_config = ConfigDict(from_attributes=True)


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
    parsed_data: Optional[Any] = None
    subjects: List[SubjectWithChapters] = []
    processing_error: Optional[str] = None
    is_processed: bool = False
    is_ai_processed: bool = False
    extracted_text: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def subject(self) -> str:
        return self.title

    @computed_field
    @property
    def units(self) -> List[UnitOut]:
        result: List[UnitOut] = []
        for s in self.subjects:
            # Aggregate topics and hours from the subject's chapters.
            # When a syllabus has one chapter per unit (the common case),
            # this yields that chapter's topics and hours directly.
            all_topics: List[str] = []
            total_hours = 0
            for chap in s.chapters:
                if chap.estimated_hours:
                    total_hours += chap.estimated_hours
                if chap.topics:
                    if isinstance(chap.topics, list):
                        all_topics.extend(str(t) for t in chap.topics)
                    elif isinstance(chap.topics, dict):
                        all_topics.extend(str(v) for v in chap.topics.values())
            result.append(
                UnitOut(
                    unitNumber=s.order + 1,
                    title=s.name,
                    description=s.description,
                    estimatedHours=total_hours,
                    topics=all_topics if all_topics else None,
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
