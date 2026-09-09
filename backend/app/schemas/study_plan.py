"""
Study Plan schemas
"""
from datetime import date
from typing import Optional, List, Any

from pydantic import BaseModel, Field, model_validator


class StudyPlanBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None
    exam_date: Optional[date] = None
    syllabus_id: Optional[int] = None

    @model_validator(mode="after")
    def validate_dates(self) -> "StudyPlanBase":
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        if self.exam_date and self.exam_date < self.start_date:
            raise ValueError("exam_date must be on or after start_date")
        return self


class StudyPlanCreate(StudyPlanBase):
    is_ai_generated: bool = False


class StudyPlanUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    exam_date: Optional[date] = None
    is_active: Optional[bool] = None
    plan_data: Optional[Any] = None

    @model_validator(mode="after")
    def validate_dates(self) -> "StudyPlanUpdate":
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        if self.exam_date and self.start_date and self.exam_date < self.start_date:
            raise ValueError("exam_date must be on or after start_date")
        return self


class StudyTaskBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    subject_id: Optional[int] = None
    chapter_id: Optional[int] = None
    due_date: Optional[date] = None
    task_type: Optional[str] = None


class StudyTaskCreate(StudyTaskBase):
    pass


class StudyTaskUpdate(BaseModel):
    completed: Optional[bool] = None
    due_date: Optional[date] = None


class StudyTaskOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    subject_id: Optional[int] = None
    chapter_id: Optional[int] = None
    due_date: Optional[date] = None
    completed: bool
    task_type: Optional[str] = None

    class Config:
        from_attributes = True


class StudyPlanOut(StudyPlanBase):
    id: int
    is_active: bool
    plan_data: Optional[Any] = None
    tasks: List[StudyTaskOut] = []

    class Config:
        from_attributes = True
