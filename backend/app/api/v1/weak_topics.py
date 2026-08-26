"""
Weak Topics API endpoints
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.auth import get_current_user_id
from app.database.database import get_db
from app.models.progress import WeakTopic
from app.services.progress_service import ProgressService

router = APIRouter()
progress_service = ProgressService()


@router.get("/")
async def list_weak_topics(
    syllabus_id: Optional[int] = None,
    min_accuracy: Optional[float] = None,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    query = select(WeakTopic).where(WeakTopic.user_id == user_id)
    if syllabus_id:
        query = query.where(WeakTopic.syllabus_id == syllabus_id)
    if min_accuracy:
        query = query.where(WeakTopic.accuracy < min_accuracy)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/detect")
async def detect_weak_topics(
    syllabus_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return await progress_service.detect_weak_topics(user_id, syllabus_id, db)


@router.get("/{topic_id}")
async def get_weak_topic(
    topic_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(WeakTopic).where(WeakTopic.id == topic_id, WeakTopic.user_id == user_id)
    )
    topic = result.scalars().first()
    if not topic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Weak topic not found")
    return topic
