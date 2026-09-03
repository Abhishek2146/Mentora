"""
Exam Simulator API endpoints
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user_id
from app.database.database import get_db
from app.services.exam_service import ExamService
from app.services.quiz_service import QuizService

router = APIRouter()
exam_service = ExamService()
quiz_service = QuizService()


class GenerateExamRequest(BaseModel):
    syllabus_id: Optional[int] = None
    num_questions: int = Field(20, ge=5, le=40)
    duration_minutes: int = Field(45, ge=5, le=240)
    subject_filter: Optional[List[str]] = None


@router.post("/generate")
async def generate_exam(
    req: GenerateExamRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Generate a timed mock exam covering the student's syllabus."""
    try:
        return await exam_service.generate_exam(
            user_id=user_id,
            db=db,
            syllabus_id=req.syllabus_id,
            num_questions=req.num_questions,
            duration_minutes=req.duration_minutes,
            subject_filter=req.subject_filter,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
