"""
Admin API endpoints

Super-admin-only management endpoints for platform overview,
user management, and membership control. All routes require an
authenticated super admin.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.auth import require_super_admin
from app.database.database import get_db
from app.models.user import User, UserRole
from app.models.subscription import (
    Subscription,
    PlanType,
    BillingCycle,
    SubscriptionStatus,
)
from app.models.syllabus import Syllabus
from app.models.study_plan import StudyPlan
from app.models.quiz import Quiz, QuizAttempt
from app.models.coding_problem import CodingProblem, CodingSubmission
from app.models.flashcard import FlashcardDeck
from app.schemas.user import UserOut, AdminUserUpdate
from app.schemas.subscription import AdminSubscriptionOut
from app.services.subscription_service import subscription_service

router = APIRouter()


# --------------------------------------------------
# Request schemas for membership management
# --------------------------------------------------

class GrantMembershipRequest(BaseModel):
    """Grant premium membership to a user."""
    billing_cycle: BillingCycle = BillingCycle.MONTHLY
    auto_renew: bool = False


class RevokeMembershipRequest(BaseModel):
    """Revoke premium membership from a user."""
    pass


# --------------------------------------------------
# User + subscription combined response
# --------------------------------------------------

class UserWithMembershipOut(BaseModel):
    """User profile combined with their subscription info."""
    user: UserOut
    subscription: Optional[AdminSubscriptionOut] = None

    class Config:
        from_attributes = True


# --------------------------------------------------
# Dashboard
# --------------------------------------------------

@router.get("/dashboard")
async def admin_dashboard(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    """Aggregated platform statistics for the admin dashboard."""

    total_users = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    total_students = (
        await db.execute(
            select(func.count()).select_from(User).where(User.role == UserRole.STUDENT.value)
        )
    ).scalar() or 0
    total_admins = (
        await db.execute(
            select(func.count()).select_from(User).where(User.role == UserRole.ADMIN.value)
        )
    ).scalar() or 0
    total_super_admins = (
        await db.execute(
            select(func.count()).select_from(User).where(User.role == UserRole.SUPER_ADMIN.value)
        )
    ).scalar() or 0
    active_users = (
        await db.execute(
            select(func.count()).select_from(User).where(User.is_active == True)
        )
    ).scalar() or 0

    total_syllabi = (await db.execute(select(func.count()).select_from(Syllabus))).scalar() or 0
    total_study_plans = (await db.execute(select(func.count()).select_from(StudyPlan))).scalar() or 0
    total_quizzes = (await db.execute(select(func.count()).select_from(Quiz))).scalar() or 0
    total_quiz_attempts = (await db.execute(select(func.count()).select_from(QuizAttempt))).scalar() or 0
    total_coding_problems = (await db.execute(select(func.count()).select_from(CodingProblem))).scalar() or 0
    total_coding_submissions = (await db.execute(select(func.count()).select_from(CodingSubmission))).scalar() or 0
    total_flashcard_decks = (await db.execute(select(func.count()).select_from(FlashcardDeck))).scalar() or 0

    avg_quiz_score = (
        await db.execute(select(func.avg(QuizAttempt.score)))
    ).scalar() or 0.0

    recent_registrations = (
        await db.execute(select(User).order_by(User.created_at.desc()).limit(5))
    ).scalars().all()

    return {
        "stats": {
            "total_users": total_users,
            "total_students": total_students,
            "total_admins": total_admins,
            "total_super_admins": total_super_admins,
            "active_users": active_users,
            "total_syllabi": total_syllabi,
            "total_study_plans": total_study_plans,
            "total_quizzes": total_quizzes,
            "total_quiz_attempts": total_quiz_attempts,
            "total_coding_problems": total_coding_problems,
            "total_coding_submissions": total_coding_submissions,
            "total_flashcard_decks": total_flashcard_decks,
            "avg_quiz_score": round(float(avg_quiz_score), 2),
        },
        "recent_registrations": [
            {
                "id": u.id,
                "username": u.username,
                "full_name": u.full_name,
                "email": u.email,
                "role": u.role,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in recent_registrations
        ],
    }


# --------------------------------------------------
# User listing
# --------------------------------------------------

@router.get("/users", response_model=List[UserOut])
async def list_users(
    role: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    """List all users, optionally filtered by role or search term."""
    query = select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)

    if role:
        query = query.where(User.role == role)

    if search:
        like = f"%{search}%"
        query = query.where(
            (User.email.ilike(like))
            | (User.username.ilike(like))
            | (User.full_name.ilike(like))
        )

    result = await db.execute(query)
    return result.scalars().all()


# --------------------------------------------------
# User detail with membership
# --------------------------------------------------

@router.get("/users/{user_id}", response_model=UserWithMembershipOut)
async def get_user_with_membership(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    """Get a specific user with their subscription details."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    subscription = await subscription_service.get_subscription(db, user_id)
    if subscription:
        await subscription_service.resolve_effective_plan(db, subscription)

    return UserWithMembershipOut(
        user=UserOut.model_validate(user),
        subscription=AdminSubscriptionOut.model_validate(subscription) if subscription else None,
    )


# --------------------------------------------------
# User update
# --------------------------------------------------

@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    user_data: AdminUserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot modify their own account here",
        )

    update_data = user_data.dict(exclude_unset=True)
    if "role" in update_data and update_data["role"] is not None:
        role = update_data["role"]
        update_data["role"] = role.value if hasattr(role, "value") else role

    for field, value in update_data.items():
        setattr(user, field, value)

    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# --------------------------------------------------
# User delete
# --------------------------------------------------

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot delete their own account",
        )

    await db.delete(user)
    await db.commit()
    return None


# --------------------------------------------------
# Membership management
# --------------------------------------------------

@router.post("/users/{user_id}/grant-membership", response_model=AdminSubscriptionOut)
async def grant_membership(
    user_id: int,
    payload: GrantMembershipRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    """Grant premium membership to a user. Does not change the user's role."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    subscription = await subscription_service.activate_subscription(
        db,
        user_id,
        billing_cycle=payload.billing_cycle,
        auto_renew=payload.auto_renew,
    )
    return subscription


@router.post("/users/{user_id}/revoke-membership", response_model=AdminSubscriptionOut)
async def revoke_membership(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    """Revoke premium membership. Sets plan to FREE without deleting records."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    subscription = await subscription_service.revoke_subscription(db, user_id)
    return subscription
