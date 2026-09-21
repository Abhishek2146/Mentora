# Study Streak schemas

from typing import List, Optional, Dict, Any
from datetime import datetime

from pydantic import BaseModel, Field


class StudyStreakOut(BaseModel):
    id: int
    user_id: int
    current_streak: int
    longest_streak: int
    total_study_days: int
    total_study_minutes: int
    last_qualifying_date: Optional[datetime] = None

    class Config:
        from_attributes = True


class DailyStudySummaryOut(BaseModel):
    id: int
    user_id: int
    date: str
    study_minutes: int
    qualifying: bool
    activity_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_new_record: Optional[bool] = False
    message: Optional[str] = None

    class Config:
        from_attributes = True


class StudyActivitySummary(BaseModel):
    current_streak: int
    longest_streak: int
    total_study_days: int
    total_study_minutes: int
    today_study_minutes: int
    today_qualifying: bool
    avg_qualifying_minutes: float
    calendar_data: List[Dict[str, Any]]


class RecordStudySession(BaseModel):
    study_minutes: int = Field(..., ge=0, description="Study minutes completed")
    activity_count: int = Field(
        default=1, ge=0, description="Number of activities completed"
    )
    date_str: Optional[str] = Field(
        default=None, description="Date in YYYY-MM-DD format (defaults to today)"
    )


class StudyCalendarDay(BaseModel):
    date: str
    day_of_week: str
    study_minutes: int
    qualifying: bool
    heatmap_level: int  # 0=none, 1=1-29min, 2=30-59min, 3=60-119min, 4=120+min