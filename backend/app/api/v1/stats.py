"""
Public landing-page statistics endpoints.
"""
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.models.flashcard import Flashcard
from app.models.quiz import QuizAttempt
from app.models.review import Review
from app.models.user import User, UserRole

router = APIRouter()


class PublicStats(BaseModel):
    total_students: int
    total_flashcards: int
    quiz_pass_rate: Optional[float] = None
    total_reviews: int
    average_rating: Optional[float] = None


@router.get("/public", response_model=PublicStats)
async def get_public_stats(
    db: AsyncSession = Depends(get_db),
):
    """Real platform stats for the landing page (no fake numbers)."""
    students = await db.execute(
        select(func.count(User.id)).where(User.role == UserRole.STUDENT.value)
    )
    total_students = int(students.scalar() or 0)

    flashcards = await db.execute(select(func.count(Flashcard.id)))
    total_flashcards = int(flashcards.scalar() or 0)

    attempts = await db.execute(select(func.count(QuizAttempt.id)))
    total_attempts = int(attempts.scalar() or 0)
    passed = await db.execute(
        select(func.count(QuizAttempt.id)).where(QuizAttempt.is_passed.is_(True))
    )
    total_passed = int(passed.scalar() or 0)
    quiz_pass_rate = (
        round((total_passed / total_attempts) * 100, 1) if total_attempts > 0 else None
    )

    rating = await db.execute(
        select(
            func.count(Review.id),
            func.coalesce(func.avg(Review.rating), 0),
        )
    )
    review_count, avg_rating = rating.one()
    total_reviews = int(review_count or 0)
    average_rating = (
        round(float(avg_rating), 1) if total_reviews > 0 else None
    )

    return PublicStats(
        total_students=total_students,
        total_flashcards=total_flashcards,
        quiz_pass_rate=quiz_pass_rate,
        total_reviews=total_reviews,
        average_rating=average_rating,
    )