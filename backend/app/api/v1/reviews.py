"""
Reviews API endpoints
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user_id
from app.core.logger import get_logger
from app.database.database import get_db
from app.models.review import Review
from app.models.user import User
from app.schemas.review import ReviewCreate, ReviewOut, ReviewUpdate

router = APIRouter()
logger = get_logger(__name__)


class ReviewSummary(BaseModel):
    average_rating: float
    total_reviews: int


def _display_name(user: Optional[User]) -> Optional[str]:
    if not user:
        return None
    return user.full_name or user.username


@router.get("/", response_model=List[ReviewOut])
async def list_reviews(
    db: AsyncSession = Depends(get_db),
):
    """Public list of all reviews (newest first)."""
    result = await db.execute(
        select(Review, User)
        .outerjoin(User, Review.user_id == User.id)
        .order_by(Review.created_at.desc(), Review.id.desc())
    )
    reviews = []
    for review, user in result.all():
        out = ReviewOut.model_validate(review)
        out.user_name = _display_name(user)
        reviews.append(out)
    return reviews


@router.get("/summary", response_model=ReviewSummary)
async def get_review_summary(
    db: AsyncSession = Depends(get_db),
):
    """Public average rating and review count."""
    result = await db.execute(
        select(
            func.coalesce(func.avg(Review.rating), 0),
            func.count(Review.id),
        )
    )
    avg, count = result.one()
    return ReviewSummary(
        average_rating=round(float(avg or 0), 1),
        total_reviews=int(count or 0),
    )


@router.get("/me", response_model=ReviewOut)
async def get_my_review(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Return the authenticated user's review if one exists."""
    result = await db.execute(
        select(Review).where(Review.user_id == user_id)
    )
    review = result.scalars().first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No review submitted yet",
        )
    return review


@router.post("/", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
async def create_review(
    payload: ReviewCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Submit a review. Upserts: one review per user."""
    result = await db.execute(
        select(Review).where(Review.user_id == user_id)
    )
    existing = result.scalars().first()
    if existing:
        existing.rating = payload.rating
        existing.comment = payload.comment
        review = existing
    else:
        review = Review(user_id=user_id, rating=payload.rating, comment=payload.comment)
        db.add(review)

    await db.commit()
    await db.refresh(review)
    return review


@router.put("/me", response_model=ReviewOut)
async def update_my_review(
    payload: ReviewUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Update the authenticated user's review."""
    result = await db.execute(
        select(Review).where(Review.user_id == user_id)
    )
    review = result.scalars().first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No review submitted yet",
        )

    if payload.rating is not None:
        review.rating = payload.rating
    if payload.comment is not None:
        review.comment = payload.comment.strip() or None

    await db.commit()
    await db.refresh(review)
    return review


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_review(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Delete the authenticated user's review."""
    result = await db.execute(
        select(Review).where(Review.user_id == user_id)
    )
    review = result.scalars().first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No review submitted yet",
        )

    await db.delete(review)
    await db.commit()