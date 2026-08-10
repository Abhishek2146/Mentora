"""
Quizzes API endpoints
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.auth import get_current_user_id
from app.database.database import get_db
from app.models.quiz import Quiz, Question, QuizAttempt
from app.schemas.quiz import QuizCreate, QuizOut, QuizUpdate, QuizAttemptCreate, QuizAttemptOut
from app.services.quiz_service import QuizService

router = APIRouter()
quiz_service = QuizService()


@router.post("/", response_model=QuizOut, status_code=status.HTTP_201_CREATED)
async def create_quiz(
    quiz_data: QuizCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    new_quiz = Quiz(user_id=user_id, **quiz_data.dict())
    db.add(new_quiz)
    await db.commit()
    await db.refresh(new_quiz)

    await quiz_service.generate_questions(new_quiz, db)

    return new_quiz


@router.get("/", response_model=List[QuizOut])
async def list_quizzes(
    subject_id: Optional[int] = None,
    chapter_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    query = select(Quiz).where((Quiz.user_id == user_id) | (Quiz.user_id.is_(None)))
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
    result = await db.execute(
        select(Quiz).where(Quiz.id == quiz_id)
    )
    quiz = result.scalars().first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")
    return quiz


@router.post("/{quiz_id}/attempt", response_model=QuizAttemptOut, status_code=status.HTTP_201_CREATED)
async def submit_attempt(
    quiz_id: int,
    attempt_data: QuizAttemptCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    attempt = QuizAttempt(user_id=user_id, **attempt_data.dict())
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)
    return attempt


@router.get("/{quiz_id}/attempts", response_model=List[QuizAttemptOut])
async def get_attempts(
    quiz_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(QuizAttempt).where(QuizAttempt.quiz_id == quiz_id, QuizAttempt.user_id == user_id)
    )
    return result.scalars().all()


@router.get("/attempts/my", response_model=List[QuizAttemptOut])
async def get_my_attempts(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(QuizAttempt).where(QuizAttempt.user_id == user_id)
    )
    return result.scalars().all()
