"""
Revision API endpoints
"""
from typing import List, Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.auth import get_current_user_id
from app.database.database import get_db
from app.models.revision import RevisionSchedule, RevisionItem
from app.services.revision_service import RevisionService

router = APIRouter()
revision_service = RevisionService()


@router.post("/schedule", status_code=status.HTTP_201_CREATED)
async def create_revision_schedule(
    syllabus_id: int,
    start_date: date,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        schedule = await revision_service.generate_revision_schedule(
            user_id=user_id,
            syllabus_id=syllabus_id,
            start_date=start_date,
            end_date=end_date,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return schedule

@router.get("/schedules")
async def list_revision_schedules(
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    query = select(RevisionSchedule).where(RevisionSchedule.user_id == user_id)
    if is_active is not None:
        query = query.where(RevisionSchedule.is_active == is_active)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/schedules/{schedule_id}")
async def get_revision_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(RevisionSchedule).where(RevisionSchedule.id == schedule_id, RevisionSchedule.user_id == user_id)
    )
    schedule = result.scalars().first()
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Revision schedule not found")

    items_result = await db.execute(
        select(RevisionItem).where(RevisionItem.schedule_id == schedule_id)
    )
    items = items_result.scalars().all()

    return {"schedule": schedule, "items": items}


@router.put("/items/{item_id}")
async def complete_revision_item(
    item_id: int,
    completed: bool = True,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(RevisionItem).join(RevisionSchedule).where(
            RevisionItem.id == item_id, RevisionSchedule.user_id == user_id
        )
    )
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Revision item not found")

    item.completed = completed
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"item": item}
