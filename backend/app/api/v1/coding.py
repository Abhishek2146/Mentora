"""
Coding API endpoints
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.core.auth import get_current_user_id
from app.core.logger import get_logger
from app.core.quotas import QuotaContext, record_usage, require_ai_quota
from app.database.database import get_db
from app.models.coding_problem import CodingProblem, CodingSubmission
from app.models.subscription import UsageType
from app.models.syllabus import Syllabus
from app.schemas.coding import (
    CodingProblemCreate,
    CodingProblemOut,
    CodingSubmissionOut,
    CodingSubmitBody,
    GenerateCodingProblemRequest,
)
from app.services.coding_service import CodingService

router = APIRouter()
coding_service = CodingService()
logger = get_logger(__name__)


@router.post(
    "/generate",
    response_model=CodingProblemOut,
    status_code=status.HTTP_201_CREATED,
)
async def generate_problem(
    payload: GenerateCodingProblemRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    quota: QuotaContext = Depends(
        require_ai_quota(UsageType.CODING_PROBLEM_GENERATION)
    ),
):
    """AI-generate a coding practice problem."""
    topic = (payload.topic or "").strip()
    syllabus_context = ""

    if payload.syllabus_id:
        result = await db.execute(
            select(Syllabus).where(
                Syllabus.id == payload.syllabus_id,
                Syllabus.user_id == user_id,
            )
        )
        syllabus = result.scalars().first()
        if not syllabus:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Syllabus not found",
            )
        syllabus_context = syllabus.title or ""
        if not topic:
            topic = syllabus.title or "Programming fundamentals"
    elif not topic:
        result = await db.execute(
            select(Syllabus)
            .where(Syllabus.user_id == user_id)
            .order_by(Syllabus.id.desc())
            .limit(1)
        )
        syllabus = result.scalars().first()
        if syllabus:
            syllabus_context = syllabus.title or ""
            topic = syllabus.title or "Programming fundamentals"
        else:
            topic = "Programming fundamentals"

    try:
        problem = await coding_service.generate_and_save_problem(
            user_id=user_id,
            topic=topic,
            difficulty=payload.difficulty.value,
            language=payload.language.lower().strip(),
            syllabus_context=syllabus_context,
            syllabus_id=payload.syllabus_id,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Coding problem generation failed for user %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI service is temporarily unavailable. Please try again.",
        ) from exc

    await record_usage(db, user_id, UsageType.CODING_PROBLEM_GENERATION)
    return problem


@router.post("/problems", response_model=CodingProblemOut, status_code=status.HTTP_201_CREATED)
async def create_problem(
    problem_data: CodingProblemCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    new_problem = CodingProblem(user_id=user_id, **problem_data.model_dump())
    db.add(new_problem)
    await db.commit()
    await db.refresh(new_problem)
    return new_problem


@router.get("/problems", response_model=List[CodingProblemOut])
async def list_problems(
    difficulty: Optional[str] = None,
    category: Optional[str] = None,
    language: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    query = select(CodingProblem).where(
        CodingProblem.is_active.is_(True),
        or_(CodingProblem.user_id == user_id, CodingProblem.user_id.is_(None)),
    )
    if difficulty:
        query = query.where(CodingProblem.difficulty == difficulty)
    if category:
        query = query.where(CodingProblem.category == category)
    if language:
        query = query.where(CodingProblem.language == language.lower())
    query = query.order_by(CodingProblem.id.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/problems/{problem_id}", response_model=CodingProblemOut)
async def get_problem(
    problem_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(CodingProblem).where(
            CodingProblem.id == problem_id,
            CodingProblem.is_active.is_(True),
            or_(CodingProblem.user_id == user_id, CodingProblem.user_id.is_(None)),
        )
    )
    problem = result.scalars().first()
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found")
    return problem


@router.post(
    "/submissions/{problem_id}",
    response_model=CodingSubmissionOut,
    status_code=status.HTTP_201_CREATED,
)
async def submit_code(
    problem_id: int,
    submission_data: CodingSubmitBody,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    problem_result = await db.execute(
        select(CodingProblem).where(
            CodingProblem.id == problem_id,
            CodingProblem.is_active.is_(True),
            or_(CodingProblem.user_id == user_id, CodingProblem.user_id.is_(None)),
        )
    )
    problem = problem_result.scalars().first()
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found")

    result = await coding_service.execute_code(
        problem_id=problem_id,
        code=submission_data.code,
        language=submission_data.language,
        test_cases=problem.test_cases or [],
    )

    passed = int(result.get("passed_test_cases", 0))
    total = int(result.get("total_test_cases", 0))

    submission = CodingSubmission(
        user_id=user_id,
        problem_id=problem_id,
        code=submission_data.code,
        language=submission_data.language,
        status=result["status"],
        output=result.get("output"),
        score=int(result.get("score", 0)),
        passed_test_cases=passed,
        total_test_cases=total,
        execution_time=result.get("execution_time"),
        error_message=result.get("error_message"),
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    return submission


@router.get("/submissions/my", response_model=List[CodingSubmissionOut])
async def get_my_submissions(
    problem_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    query = select(CodingSubmission).where(CodingSubmission.user_id == user_id)
    if problem_id is not None:
        query = query.where(CodingSubmission.problem_id == problem_id)
    query = query.order_by(CodingSubmission.id.desc())
    result = await db.execute(query)
    return result.scalars().all()


class SupportedLanguagesResponse(BaseModel):
    languages: List[str]


@router.get("/languages", response_model=SupportedLanguagesResponse)
async def list_supported_languages():
    return SupportedLanguagesResponse(
        languages=sorted(coding_service.supported_languages.keys())
    )
