"""
Study Plan API endpoints
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.auth import get_current_user_id
from app.database.database import get_db
from app.models.study_plan import StudyPlan, StudyTask
from app.schemas.study_plan import StudyPlanCreate, StudyPlanOut, StudyPlanUpdate, StudyTaskCreate, StudyTaskOut, StudyTaskUpdate

router = APIRouter()


@router.post("/", response_model=StudyPlanOut, status_code=status.HTTP_201_CREATED)
async def create_study_plan(
    plan_data: StudyPlanCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    new_plan = StudyPlan(
        user_id=user_id,
        **plan_data.dict(),
    )
    db.add(new_plan)
    await db.commit()
    await db.refresh(new_plan)
    return new_plan


@router.get("/", response_model=List[StudyPlanOut])
async def list_study_plans(
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    query = select(StudyPlan).where(StudyPlan.user_id == user_id)
    if is_active is not None:
        query = query.where(StudyPlan.is_active == is_active)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{plan_id}", response_model=StudyPlanOut)
async def get_study_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(StudyPlan).where(StudyPlan.id == plan_id, StudyPlan.user_id == user_id)
    )
    plan = result.scalars().first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study plan not found")
    return plan


@router.put("/{plan_id}", response_model=StudyPlanOut)
async def update_study_plan(
    plan_id: int,
    plan_data: StudyPlanUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(StudyPlan).where(StudyPlan.id == plan_id, StudyPlan.user_id == user_id)
    )
    plan = result.scalars().first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study plan not found")

    update_data = plan_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plan, field, value)

    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_study_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(StudyPlan).where(StudyPlan.id == plan_id, StudyPlan.user_id == user_id)
    )
    plan = result.scalars().first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study plan not found")

    await db.delete(plan)
    await db.commit()
    return None


@router.post("/{plan_id}/tasks", response_model=StudyTaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    plan_id: int,
    task_data: StudyTaskCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    plan_result = await db.execute(
        select(StudyPlan).where(StudyPlan.id == plan_id, StudyPlan.user_id == user_id)
    )
    plan = plan_result.scalars().first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study plan not found")

    new_task = StudyTask(study_plan_id=plan_id, **task_data.dict())
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    return new_task


@router.get("/{plan_id}/tasks", response_model=List[StudyTaskOut])
async def list_tasks(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(StudyTask).join(StudyPlan).where(
            StudyPlan.id == plan_id, StudyPlan.user_id == user_id
        )
    )
    return result.scalars().all()


@router.put("/tasks/{task_id}", response_model=StudyTaskOut)
async def update_task(
    task_id: int,
    task_data: StudyTaskUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(StudyTask).join(StudyPlan).where(
            StudyTask.id == task_id, StudyPlan.user_id == user_id
        )
    )
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    update_data = task_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(StudyTask).join(StudyPlan).where(
            StudyTask.id == task_id, StudyPlan.user_id == user_id
        )
    )
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    await db.delete(task)
    await db.commit()
    return None
