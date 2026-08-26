"""
Subscription and usage API endpoints.

User endpoints are strictly read-only — plan_type, status, expires_at
and provider fields can only be changed by admins (or a future,
validated payment-provider webhook).
"""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user_id, require_admin
from app.core.config import settings
from app.database.database import get_db
from app.models.subscription import PlanType, Subscription, SubscriptionStatus, UsageType
from app.models.user import User
from app.schemas.subscription import (
    AdminActivateRequest,
    AdminSubscriptionOut,
    FeatureUsageOut,
    PlanInfo,
    PlansResponse,
    SubscriptionOut,
    UsageOut,
)
from app.services.rate_limit_service import rate_limiter
from app.services.subscription_service import (
    ensure_utc,
    subscription_service,
    today_utc,
)

router = APIRouter()

# Mounted separately at {API_PREFIX}/usage by main.py.
usage_router = APIRouter()


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def _build_usage_report(
    user_id: int,
    subscription: Subscription,
    effective_plan: PlanType,
    usage_rows: dict,
) -> UsageOut:
    """Assemble today's per-feature usage/remaining report."""

    limits = (
        settings.SUBSCRIPTION_DAILY_LIMITS
        if effective_plan == PlanType.SUBSCRIPTION
        else settings.FREE_DAILY_LIMITS
    )

    features = []
    for usage_type in UsageType:
        limit = int(limits.get(usage_type.value, 0))
        used = usage_rows.get(usage_type.value, 0)
        features.append(
            FeatureUsageOut(
                usage_type=usage_type.value,
                daily_limit=limit,
                used=used,
                remaining=max(0, limit - used),
                usage_date=today_utc(),
            )
        )

    return UsageOut(
        user_id=user_id,
        plan_type=subscription.plan_type,
        billing_cycle=subscription.billing_cycle,
        status=subscription.status,
        expires_at=(
            ensure_utc(subscription.expires_at)
            if subscription.expires_at
            else None
        ),
        effective_plan=effective_plan.value,
        rate_limit_per_minute=subscription_service.get_rate_limit(
            effective_plan
        ),
        features=features,
        usage_date=today_utc(),
    )


async def _get_usage_report(
    db: AsyncSession,
    user_id: int,
) -> UsageOut:
    subscription = await subscription_service.get_or_create_subscription(
        db, user_id
    )
    effective_plan, _ = await subscription_service.resolve_effective_plan(
        db, subscription
    )

    from app.models.subscription import Usage

    result = await db.execute(
        select(Usage).where(
            Usage.user_id == user_id,
            Usage.usage_date == today_utc(),
        )
    )
    usage_rows = {
        row.usage_type: row.request_count for row in result.scalars().all()
    }

    return _build_usage_report(
        user_id, subscription, effective_plan, usage_rows
    )


# --------------------------------------------------
# Public endpoints
# --------------------------------------------------

@router.get("/plans", response_model=PlansResponse)
async def list_plans():
    """Available plans and their configured limits."""
    return PlansResponse(
        plans=[
            PlanInfo(
                plan_type=PlanType.FREE.value,
                billing_cycles=["NONE"],
                rate_limit_per_minute=settings.RATE_LIMIT_FREE_PER_MINUTE,
                daily_limits=settings.FREE_DAILY_LIMITS,
            ),
            PlanInfo(
                plan_type=PlanType.SUBSCRIPTION.value,
                billing_cycles=["MONTHLY", "YEARLY"],
                rate_limit_per_minute=(
                    settings.RATE_LIMIT_SUBSCRIPTION_PER_MINUTE
                ),
                daily_limits=settings.SUBSCRIPTION_DAILY_LIMITS,
            ),
        ]
    )


# --------------------------------------------------
# Authenticated user endpoints (read-only)
# --------------------------------------------------

@router.get("/me", response_model=SubscriptionOut)
async def my_subscription(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """The authenticated user's own subscription."""
    subscription = await subscription_service.get_or_create_subscription(
        db, user_id
    )
    await subscription_service.resolve_effective_plan(db, subscription)
    return subscription


@router.get("/me/limits")
async def my_limits(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """The authenticated user's plan limits and per-minute rate limit."""
    subscription = await subscription_service.get_or_create_subscription(
        db, user_id
    )
    effective_plan, _ = await subscription_service.resolve_effective_plan(
        db, subscription
    )
    limits = (
        settings.SUBSCRIPTION_DAILY_LIMITS
        if effective_plan == PlanType.SUBSCRIPTION
        else settings.FREE_DAILY_LIMITS
    )
    return {
        "plan_type": subscription.plan_type,
        "effective_plan": effective_plan.value,
        "billing_cycle": subscription.billing_cycle,
        "status": subscription.status,
        "expires_at": subscription.expires_at,
        "rate_limit_per_minute": subscription_service.get_rate_limit(
            effective_plan
        ),
        "daily_limits": limits,
    }


# --------------------------------------------------
# Usage endpoint ({API_PREFIX}/usage/me)
# --------------------------------------------------

@usage_router.get("/me", response_model=UsageOut)
async def my_usage(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Current daily usage and remaining quota for every feature."""
    return await _get_usage_report(db, user_id)


# --------------------------------------------------
# Admin management (require_admin)
# --------------------------------------------------

@router.get("/admin", response_model=List[AdminSubscriptionOut])
async def list_subscriptions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    plan_type: Optional[PlanType] = None,
    status: Optional[SubscriptionStatus] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """List all subscriptions with optional filters."""
    query = select(Subscription).order_by(Subscription.id)
    if plan_type is not None:
        query = query.where(Subscription.plan_type == plan_type.value)
    if status is not None:
        query = query.where(Subscription.status == status.value)

    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/admin/{user_id}", response_model=AdminSubscriptionOut)
async def admin_get_subscription(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    subscription = await subscription_service.get_or_create_subscription(
        db, user_id
    )
    await subscription_service.resolve_effective_plan(db, subscription)
    return subscription


@router.post("/admin/{user_id}/activate", response_model=AdminSubscriptionOut)
async def admin_activate_subscription(
    user_id: int,
    payload: AdminActivateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Activate a paid SUBSCRIPTION plan for a user."""
    return await subscription_service.activate_subscription(
        db,
        user_id,
        billing_cycle=payload.billing_cycle,
        auto_renew=payload.auto_renew,
    )


@router.post("/admin/{user_id}/cancel", response_model=AdminSubscriptionOut)
async def admin_cancel_subscription(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Cancel a user's subscription immediately."""
    return await subscription_service.cancel_subscription(db, user_id)


@router.post("/admin/{user_id}/expire", response_model=AdminSubscriptionOut)
async def admin_expire_subscription(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Force-expire a user's subscription."""
    return await subscription_service.expire_subscription(db, user_id)
