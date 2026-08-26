"""
Coding API endpoints
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.auth import get_current_user_id
from app.database.database import get_db
from app.models.coding_problem import CodingProblem, CodingSubmission
from app.schemas.coding import CodingProblemCreate, CodingProblemOut, CodingSubmissionCreate, CodingSubmissionOut
from app.services.coding_service import CodingService

router = APIRouter()
coding_service = CodingService()


@router.post("/problems", response_model=CodingProblemOut, status_code=status.HTTP_201_CREATED)
async def create_problem(
    problem_data: CodingProblemCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    new_problem = CodingProblem(user_id=user_id, **problem_data.dict())
    db.add(new_problem)
    await db.commit()
    await db.refresh(new_problem)
    return new_problem


@router.get("/problems", response_model=List[CodingProblemOut])
async def list_problems(
    difficulty: Optional[str] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    query = select(CodingProblem).where((CodingProblem.user_id == user_id) | (CodingProblem.user_id.is_(None)))
    if difficulty:
        query = query.where(CodingProblem.difficulty == difficulty)
    if category:
        query = query.where(CodingProblem.category == category)
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
            (CodingProblem.user_id == user_id) | (CodingProblem.user_id.is_(None)),
        )
    )
    problem = result.scalars().first()
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found")
    return problem


@router.post("/submissions/{problem_id}", response_model=CodingSubmissionOut, status_code=status.HTTP_201_CREATED)
async def submit_code(
    problem_id: int,
    submission_data: CodingSubmissionCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    problem_result = await db.execute(
        select(CodingProblem).where(
            CodingProblem.id == problem_id,
            (CodingProblem.user_id == user_id) | (CodingProblem.user_id.is_(None)),
        )
    )
    problem = problem_result.scalars().first()
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found")

    result = await coding_service.execute_code(problem_id, submission_data.code, submission_data.language)

    # coding_service.execute_code only reports overall pass/fail from the
    # program's exit code - it does not grade against CodingProblem's
    # individual test_cases. That's a separate, larger gap in the grading
    # logic (out of scope here); this just maps the overall result onto
    # the real CodingSubmission columns instead of the nonexistent
    # passed/memory_used ones that were crashing every submission.
    passed = bool(result.get("passed"))

    submission = CodingSubmission(
        user_id=user_id,
        problem_id=problem_id,
        code=submission_data.code,
        language=submission_data.language,
        status=result["status"],
        output=result["output"],
        score=100 if passed else 0,
        passed_test_cases=1 if passed else 0,
        total_test_cases=1,
        execution_time=result.get("execution_time"),
        error_message=result["output"] if result["status"] in ("error", "timeout") else None,
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    return submission


@router.get("/submissions/my", response_model=List[CodingSubmissionOut])
async def get_my_submissions(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(CodingSubmission).where(CodingSubmission.user_id == user_id)
    )
    return result.scalars().all()
