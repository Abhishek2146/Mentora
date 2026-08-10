"""
Analytics API endpoints
"""
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.auth import get_current_user_id
from app.database.database import get_db
from app.models.quiz import QuizAttempt
from app.models.study_plan import StudyTask
from app.models.coding_problem import CodingSubmission
from app.models.progress import Progress
from app.schemas.common import ResponseModel
from app.services.analytics_service import AnalyticsService

router = APIRouter()
analytics_service = AnalyticsService()


@router.get("/dashboard", response_model=ResponseModel)
async def get_dashboard_analytics(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return await analytics_service.get_dashboard_analytics(user_id, db)


@router.get("/study-time", response_model=List)
async def get_study_time_trend(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return await analytics_service.get_study_time_trend(user_id, days, db)


@router.get("/quiz-performance", response_model=List)
async def get_quiz_performance(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return await analytics_service.get_quiz_performance(user_id, db)


@router.get("/subject-breakdown", response_model=List)
async def get_subject_breakdown(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return await analytics_service.get_subject_breakdown(user_id, db)


@router.get("/activity", response_model=List)
async def get_activity_log(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return await analytics_service.get_activity_log(user_id, limit, db)
