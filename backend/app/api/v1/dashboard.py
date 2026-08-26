"""
Dashboard API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.auth import get_current_user_id
from app.database.database import get_db
from app.models.user import User
from app.models.syllabus import Syllabus
from app.models.study_plan import StudyPlan, StudyTask
from app.models.quiz import Quiz, QuizAttempt
from app.models.coding_problem import CodingSubmission
from app.models.progress import Progress
from app.services.analytics_service import AnalyticsService

router = APIRouter()
analytics_service = AnalyticsService()


@router.get("/")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    syllabus_result = await db.execute(
        select(func.count()).select_from(Syllabus).where(Syllabus.user_id == user_id)
    )
    syllabi_count = syllabus_result.scalar()

    active_plans_result = await db.execute(
        select(func.count()).select_from(StudyPlan).where(
            StudyPlan.user_id == user_id, StudyPlan.is_active == True
        )
    )
    active_plans_count = active_plans_result.scalar()

    pending_tasks_result = await db.execute(
        select(func.count()).select_from(StudyTask).join(StudyPlan).where(
            StudyPlan.user_id == user_id, StudyTask.completed == False
        )
    )
    pending_tasks_count = pending_tasks_result.scalar()

    attempts_result = await db.execute(
        select(func.count()).select_from(QuizAttempt).where(QuizAttempt.user_id == user_id)
    )
    total_attempts = attempts_result.scalar()

    avg_score_result = await db.execute(
        select(func.avg(QuizAttempt.score)).select_from(QuizAttempt).where(QuizAttempt.user_id == user_id)
    )
    avg_score = avg_score_result.scalar() or 0.0

    coding_result = await db.execute(
        select(func.count()).select_from(CodingSubmission).where(
            CodingSubmission.user_id == user_id, CodingSubmission.passed == True
        )
    )
    coding_solved = coding_result.scalar()

    progress_result = await db.execute(
        select(Progress).where(
            Progress.user_id == user_id, Progress.progress_type == "overall"
        )
    )
    progress = progress_result.scalars().first()

    upcoming_tasks_result = await db.execute(
        select(StudyTask)
        .join(StudyPlan)
        .where(StudyPlan.user_id == user_id, StudyTask.completed == False)
        .order_by(StudyTask.due_date)
        .limit(5)
    )
    upcoming_tasks = upcoming_tasks_result.scalars().all()

    card_stats = await analytics_service.get_dashboard_stats(user_id, db)

    return {
        "user": {"username": user.username, "full_name": user.full_name, "role": user.role.value if hasattr(user.role, "value") else user.role},
        "stats": {
            "syllabi_count": syllabi_count,
            "active_plans": active_plans_count,
            "pending_tasks": pending_tasks_count,
            "total_attempts": total_attempts,
            "avg_score": float(avg_score),
            "coding_solved": coding_solved,
        },
        "cards": card_stats,
        "overall_progress": progress.value if progress else 0.0,
        "upcoming_tasks": [
            {
                "id": t.id,
                "title": t.title,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "task_type": t.task_type,
            }
            for t in upcoming_tasks
        ],
    }
