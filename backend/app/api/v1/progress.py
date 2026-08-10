"""
Progress API endpoints
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.auth import get_current_user_id
from app.database.database import get_db
from app.models.progress import Progress, WeakTopic
from app.schemas.progress import ProgressCreate, ProgressOut, WeakTopicOut

router = APIRouter()


@router.post("/", response_model=ProgressOut, status_code=status.HTTP_201_CREATED)
async def create_progress(
    progress_data: ProgressCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    new_progress = Progress(
        user_id=user_id,
        progress_type=progress_data.progress_type,
        value=progress_data.value,
        target_value=progress_data.target_value,
        syllabus_id=progress_data.syllabus_id,
        subject_id=progress_data.subject_id,
        chapter_id=progress_data.chapter_id,
        metadata=progress_data.metadata,
    )
    db.add(new_progress)
    await db.commit()
    await db.refresh(new_progress)
    return new_progress


@router.get("/", response_model=List[ProgressOut])
async def list_progress(
    progress_type: Optional[str] = None,
    syllabus_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    query = select(Progress).where(Progress.user_id == user_id)
    if progress_type:
        query = query.where(Progress.progress_type == progress_type)
    if syllabus_id:
        query = query.where(Progress.syllabus_id == syllabus_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{progress_id}", response_model=ProgressOut)
async def get_progress(
    progress_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(Progress).where(Progress.id == progress_id, Progress.user_id == user_id)
    )
    progress = result.scalars().first()
    if not progress:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Progress not found")
    return progress


@router.get("/weak-topics", response_model=List[WeakTopicOut])
async def get_weak_topics(
    syllabus_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    query = select(WeakTopic).where(WeakTopic.user_id == user_id)
    if syllabus_id:
        query = query.where(WeakTopic.syllabus_id == syllabus_id)
    result = await db.execute(query)
    return result.scalars().all()
