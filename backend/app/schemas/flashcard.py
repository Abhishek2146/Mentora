"""
Flashcard schemas
"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class FlashcardDeckBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    syllabus_id: Optional[int] = None
    subject_id: Optional[int] = None
    chapter_id: Optional[int] = None
    is_ai_generated: bool = False


class FlashcardDeckCreate(FlashcardDeckBase):
    pass


class FlashcardDeckUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class FlashcardBase(BaseModel):
    front: str
    back: str
    difficulty: str = Field("unknown", max_length=20)
    ease_factor: int = 250
    interval: int = 1
    repetitions: int = 0
    next_review: Optional[str] = None
    last_reviewed: Optional[str] = None

    class Config:
        from_attributes = True


class FlashcardCreate(FlashcardBase):
    pass


class FlashcardUpdate(BaseModel):
    difficulty: Optional[str] = None
    ease_factor: Optional[int] = None
    interval: Optional[int] = None
    repetitions: Optional[int] = None
    next_review: Optional[str] = None
    last_reviewed: Optional[str] = None


class FlashcardOut(FlashcardBase):
    id: int
    deck_id: int

    class Config:
        from_attributes = True


class FlashcardDeckOut(FlashcardDeckBase):
    id: int
    flashcards: List[FlashcardOut] = []

    class Config:
        from_attributes = True
