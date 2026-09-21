# Study Streak API Endpoints

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select, func
from app.core.auth import get_current_user_id
from app.database.database import get_db
from app.models.user import User
from app.models.study_streak import UserStreak, DailyStudySummary
from app.schemas.study_streak import (
    StudyStreakOut,
    DailyStudySummaryOut,
    StudyActivitySummary,
    RecordStudySession,
)
from app.services.study_streak_service import StudyStreakService

router = APIRouter()


def get_streak_service(db: AsyncSession = Depends(get_db)) -> StudyStreakService:
    return StudyStreakService(db)


@router.get("/streak", response_model=StudyStreakOut)
async def get_study_streak(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Get the user's current study streak."""
    service = get_streak_service(db)
    return await service.get_streak(user_id=user_id)


@router.post("/recalculate")
async def recalculate_streak(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Recalculate the user's study streak."""
    service = get_streak_service(db)
    return await service.recalculate_streak(user_id=user_id)


@router.post("/session", response_model=DailyStudySummaryOut)
async def record_study_session(
    session_data: RecordStudySession,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Record a study session and update streak."""
    service = get_streak_service(db)
    return await service.record_study_session(
        user_id=user_id,
        study_minutes=session_data.study_minutes,
        activity_count=session_data.activity_count,
        date_str=session_data.date_str,
    )


@router.get("/calendar", response_model=List[Dict[str, Any]])
async def get_study_calendar(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Get study calendar heatmap data."""
    service = get_streak_service(db)
    return await service.get_study_calendar(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/today", response_model=DailyStudySummaryOut)
async def get_today_study(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Get today's study summary."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    service = get_streak_service(db)
    return await service.get_daily_summary(user_id=user_id, date_str=today)


@router.get("/activity", response_model=StudyActivitySummary)
async def get_study_activity_summary(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Get study activity summary for analytics."""
    service = get_streak_service(db)
    # Get current streak
    streak_result = await db.execute(
        select(UserStreak).where(UserStreak.user_id == user_id)
    )
    streak = streak_result.scalars().first()

    # Get today's study
    today = datetime.utcnow().strftime("%Y-%m-%d")
    today_result = await db.execute(
        select(DailyStudySummary).where(
            DailyStudySummary.user_id == user_id,
            DailyStudySummary.date == today,
        )
    )
    today_summary = today_result.scalars().first()

    # Get total study days
    total_days_result = await db.execute(
        select(func.count()).select_from(DailyStudySummary).where(
            DailyStudySummary.user_id == user_id,
            DailyStudySummary.qualifying == True,
        )
    )
    total_qualifying_days = total_days_result.scalar() or 0

    # Get total study minutes
    total_minutes_result = await db.execute(
        select(func.sum(DailyStudySummary.study_minutes)).where(
            DailyStudySummary.user_id == user_id,
            DailyStudySummary.qualifying == True,
        )
    )
    total_minutes = total_minutes_result.scalar() or 0

    # Get heatmap data for last 30 days
    calendar_data = await service.get_study_calendar(user_id=user_id)

    # Calculate average study minutes on qualifying days
    qualifying_minutes_result = await db.execute(
        select(func.sum(DailyStudySummary.study_minutes)).where(
            DailyStudySummary.user_id == user_id,
            DailyStudySummary.qualifying == True,
        )
    )
    total_qualifying_minutes = qualifying_minutes_result.scalar() or 0
    avg_qualifying_minutes = (
        round(total_qualifying_minutes / total_qualifying_days, 1)
        if total_qualifying_days > 0
        else 0
    )

    return StudyActivitySummary(
        current_streak=streak.current_streak if streak else 0,
        longest_streak=streak.longest_streak if streak else 0,
        total_study_days=total_qualifying_days,
        total_study_minutes=total_minutes,
        today_study_minutes=today_summary.study_minutes if today_summary else 0,
        today_qualifying=today_summary.qualifying if today_summary else False,
        avg_qualifying_minutes=avg_qualifying_minutes,
        calendar_data=calendar_data,
    )