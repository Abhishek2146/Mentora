
"""
Reports API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.auth import get_current_user_id
from app.database.database import get_db
from app.models.chat_history import WeeklyReport
from app.services.report_service import ReportService
from app.database.database import get_db


router = APIRouter()
report_service = ReportService()


@router.get("/weekly", response_model=list)
async def get_weekly_reports(
    limit: int = 12,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(WeeklyReport)
        .where(WeeklyReport.user_id == user_id)
        .order_by(WeeklyReport.week_start.desc())
        .limit(limit)
    )

    return result.scalars().all()


@router.get("/weekly/{week_start}", response_model=dict)
async def get_weekly_report(
    week_start: str,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(WeeklyReport).where(
            WeeklyReport.user_id == user_id,
            WeeklyReport.week_start == week_start,
        )
    )

    report = result.scalars().first()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Weekly report not found",
        )

    return report


@router.post(
    "/generate-weekly",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
)
async def generate_weekly_report(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    report = await report_service.generate_weekly_report(
        user_id,
        db,
    )

    return report

