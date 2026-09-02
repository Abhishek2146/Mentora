"""
Quizzes API endpoints
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.auth import get_current_user_id
from app.core.logger import get_logger
from app.core.quotas import QuotaContext, record_usage, require_ai_quota
from app.database.database import get_db
from app.models.quiz import Quiz, Question, QuizAttempt
from app.models.subscription import UsageType
from app.schemas.quiz import (
    QuizCreate,
    QuizOut,
    QuizUpdate,
    QuizAttemptSubmit,
    QuizAttemptOut,
    QuizAttemptResultOut,
    QuestionOut,
)
from app.services.quiz_service import QuizService
from app.services.progress_service import ProgressService

router = APIRouter()
quiz_service = QuizService()
progress_service = ProgressService()
logger = get_logger(__name__)


async def _refresh_weak_topics(user_id: int, db: AsyncSession) -> None:
    """Best-effort weak-topic refresh so analytics pages stay current."""
    try:
        await progress_service.detect_weak_topics(user_id, None, db)
    except Exception:  # noqa: BLE001
        logger.warning("Weak-topic refresh failed for user %s", user_id, exc_info=True)


class GenerateMCQRequest(BaseModel):
    topic: Optional[str] = None
    difficulty: str = Field("medium", pattern="^(easy|medium|hard)$")
    count: int = Field(5, ge=1, le=20)


class SubmitQuizRequest(BaseModel):
    answers: List[dict]
    time_taken_seconds: Optional[int] = None


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


@router.get("/daily")
async def get_daily_quiz(
    count: int = 5,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Today's quiz (created on first request of the day) with its questions."""
    try:
        quiz = await quiz_service.get_or_create_daily_quiz(user_id=user_id, count=count, db=db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    result = await db.execute(
        select(Question)
        .where(Question.quiz_id == quiz.id)
        .order_by(Question.question_order)
    )
    questions = result.scalars().all()
    return {
        "quiz_id": quiz.id,
        "title": quiz.title,
        "questions": [
            {
                "id": q.id,
                "question_text": q.question_text,
                "options": q.options or [],
                "correct_answer": q.correct_answer,
                "explanation": q.explanation,
                "difficulty": str(q.difficulty).capitalize(),
            }
            for q in questions
        ],
    }


@router.post("/daily/regenerate")
async def regenerate_daily_quiz(
    count: int = 5,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Delete today's cached quiz and generate a fresh one from syllabus."""
    from datetime import date as date_cls
    today_str = date_cls.today().isoformat()
    result = await db.execute(
        select(Quiz).where(
            Quiz.user_id == user_id,
            Quiz.title == f"Daily Quiz - {today_str}",
        )
    )
    old_quiz = result.scalars().first()
    if old_quiz:
        await db.delete(old_quiz)
        await db.commit()
    try:
        quiz = await quiz_service.get_or_create_daily_quiz(user_id=user_id, count=count, db=db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    q_result = await db.execute(
        select(Question)
        .where(Question.quiz_id == quiz.id)
        .order_by(Question.question_order)
    )
    questions = q_result.scalars().all()
    return {
        "quiz_id": quiz.id,
        "title": quiz.title,
        "questions": [
            {
                "id": q.id,
                "question_text": q.question_text,
                "options": q.options or [],
                "correct_answer": q.correct_answer,
                "explanation": q.explanation,
                "difficulty": str(q.difficulty).capitalize(),
            }
            for q in questions
        ],
    }


@router.post("/generate-mcq", response_model=QuizOut, status_code=status.HTTP_201_CREATED)
async def generate_mcq(
    req: GenerateMCQRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Generate an AI MCQ quiz for a syllabus topic."""
    try:
        quiz = await quiz_service.generate_mcq_for_topic(
            user_id=user_id,
            topic=req.topic or "",
            difficulty=req.difficulty,
            count=req.count,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return await _get_accessible_quiz(quiz.id, db, user_id)


@router.post("/{quiz_id}/submit")
async def submit_quiz(
    quiz_id: int,
    body: SubmitQuizRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Grade a submitted quiz attempt and save it."""
    try:
        result = await quiz_service.submit_quiz(
            quiz_id=quiz_id,
            user_id=user_id,
            answers=body.answers,
            time_taken_seconds=body.time_taken_seconds,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    await _refresh_weak_topics(user_id, db)
    return result



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

    try:
        await quiz_service.generate_questions(new_quiz, db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Quiz created but question generation failed: {e}",
        )

    # Usage is recorded only after question generation succeeded.
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
        .where((Quiz.user_id == user_id) | (Quiz.user_id.is_(None)))
        .options(selectinload(Quiz.questions))
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

    await _refresh_weak_topics(user_id, db)

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
