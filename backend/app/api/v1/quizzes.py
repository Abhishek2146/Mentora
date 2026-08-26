"""
Quizzes API endpoints
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.auth import get_current_user_id
from app.core.quotas import QuotaContext, record_usage, require_ai_quota
from app.database.database import get_db
from app.models.quiz import Quiz, QuizAttempt
from app.models.subscription import UsageType
from app.schemas.quiz import (
    QuizCreate,
    QuizOut,
    QuizAttemptSubmit,
    QuizAttemptOut,
    QuizAttemptResultOut,
)
from app.services.quiz_service import QuizService

router = APIRouter()
quiz_service = QuizService()


async def _get_accessible_quiz(
    quiz_id: int,
    db: AsyncSession,
    user_id: int,
) -> Optional[Quiz]:
    """Fetch a quiz the user may access: own quizzes or global (user_id NULL)."""
    result = await db.execute(
        select(Quiz)
        .options(selectinload(Quiz.questions))
        .where(
            Quiz.id == quiz_id,
            (Quiz.user_id == user_id) | (Quiz.user_id.is_(None)),
        )
    )
    return result.scalars().first()


@router.post("/", response_model=QuizOut, status_code=status.HTTP_201_CREATED)
async def create_quiz(
    quiz_data: QuizCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    quota: QuotaContext = Depends(require_ai_quota(UsageType.QUIZ_GENERATION)),
):
    new_quiz = Quiz(user_id=user_id, **quiz_data.dict())
    db.add(new_quiz)
    await db.commit()
    await db.refresh(new_quiz)

    await quiz_service.generate_questions(new_quiz, db)
    await record_usage(db, user_id, UsageType.QUIZ_GENERATION)

    result = await db.execute(
        select(Quiz)
        .options(selectinload(Quiz.questions))
        .where(Quiz.id == new_quiz.id)
    )
    return result.scalars().first()


@router.get("/attempts/my", response_model=List[QuizAttemptOut])
async def get_my_attempts(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(QuizAttempt)
        .where(QuizAttempt.user_id == user_id)
        .order_by(QuizAttempt.created_at.desc())
    )
    return result.scalars().all()


@router.get("/", response_model=List[QuizOut])
async def list_quizzes(
    subject_id: Optional[int] = None,
    chapter_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    query = (
        select(Quiz)
        .options(selectinload(Quiz.questions))
        .where((Quiz.user_id == user_id) | (Quiz.user_id.is_(None)))
    )
    if subject_id:
        query = query.where(Quiz.subject_id == subject_id)
    if chapter_id:
        query = query.where(Quiz.chapter_id == chapter_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{quiz_id}", response_model=QuizOut)
async def get_quiz(
    quiz_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    quiz = await _get_accessible_quiz(quiz_id, db, user_id)
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")
    return quiz


@router.post(
    "/{quiz_id}/attempt",
    response_model=QuizAttemptResultOut,
    status_code=status.HTTP_201_CREATED,
)
async def submit_attempt(
    quiz_id: int,
    attempt_data: QuizAttemptSubmit,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    quiz = await _get_accessible_quiz(quiz_id, db, user_id)
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")

    grading = await quiz_service.grade_attempt(quiz_id, attempt_data.answers, db)
    if grading is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")

    attempt = QuizAttempt(
        user_id=user_id,
        quiz_id=quiz_id,
        score=grading["score"],
        total_questions=grading["total_questions"],
        correct_answers=grading["correct_answers"],
        incorrect_answers=grading["incorrect_answers"],
        unanswered_questions=grading["unanswered_questions"],
        time_taken=attempt_data.time_taken,
        answers=attempt_data.answers,
        is_passed=grading["is_passed"],
    )
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)

    return {
        "id": attempt.id,
        "user_id": attempt.user_id,
        "quiz_id": attempt.quiz_id,
        "score": attempt.score,
        "total_questions": attempt.total_questions,
        "correct_answers": attempt.correct_answers,
        "incorrect_answers": attempt.incorrect_answers,
        "unanswered_questions": attempt.unanswered_questions,
        "time_taken": attempt.time_taken,
        "answers": attempt.answers,
        "is_passed": attempt.is_passed,
        "created_at": attempt.created_at,
        "results": grading["results"],
    }


@router.get("/{quiz_id}/attempts", response_model=List[QuizAttemptOut])
async def get_attempts(
    quiz_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    quiz = await _get_accessible_quiz(quiz_id, db, user_id)
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")

    result = await db.execute(
        select(QuizAttempt)
        .where(QuizAttempt.quiz_id == quiz_id, QuizAttempt.user_id == user_id)
        .order_by(QuizAttempt.created_at.desc())
    )
    return result.scalars().all()
