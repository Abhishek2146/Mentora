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

from app.core.auth import get_current_user, get_current_user_id, require_admin
from app.core.config import settings
from app.database.database import get_db
from app.models.payment import Payment
from app.models.subscription import BillingCycle, PlanType, Subscription, SubscriptionStatus, UsageType
from app.models.user import User
from app.schemas.payment import (
    KhaltiInitiateRequest,
    KhaltiInitiateResponse,
    KhaltiVerifyRequest,
    KhaltiVerifyResponse,
    PaymentOut,
)
from app.schemas.subscription import (
    AdminActivateRequest,
    AdminSubscriptionOut,
    FeatureUsageOut,
    PlanInfo,
    PlansResponse,
    SubscriptionOut,
    UsageOut,
)
from app.services.khalti_service import khalti_service
from app.services.rate_limit_service import rate_limiter
from app.services.subscription_service import (
    ensure_utc,
    subscription_service,
    today_utc,
)

router = APIRouter()

# Mounted separately at {API_PREFIX}/usage by main.py.
usage_router = APIRouter()

# Khalti payments — mounted at {API_PREFIX}/subscriptions/khalti/*
khalti_router = APIRouter(prefix="/khalti", tags=["khalti"])


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
                price_monthly_paisa=settings.SUBSCRIPTION_PRICE_MONTHLY_PAISE,
                price_yearly_paisa=settings.SUBSCRIPTION_PRICE_YEARLY_PAISE,
                price_monthly_npr=round(settings.SUBSCRIPTION_PRICE_MONTHLY_PAISE / 100, 2),
                price_yearly_npr=round(settings.SUBSCRIPTION_PRICE_YEARLY_PAISE / 100, 2),
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


# --------------------------------------------------
# Khalti ePayment endpoints (user)
# --------------------------------------------------


@khalti_router.post("/initiate", response_model=KhaltiInitiateResponse)
async def khalti_initiate(
    payload: KhaltiInitiateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Initiate a Khalti payment for Mentora Pro.

    Creates a Payment row and returns payment_url for redirect.
    """
    payment, data = await khalti_service.initiate_payment(
        db, user, billing_cycle=payload.billing_cycle
    )
    return KhaltiInitiateResponse(
        pidx=payment.pidx,
        payment_url=payment.payment_url or data.get("payment_url", ""),
        expires_at=payment.expires_at,
        expires_in=data.get("expires_in"),
        purchase_order_id=payment.purchase_order_id,
        purchase_order_name=payment.purchase_order_name,
        amount=payment.amount,
        billing_cycle=payload.billing_cycle,
    )


@khalti_router.post("/verify", response_model=KhaltiVerifyResponse)
async def khalti_verify(
    payload: KhaltiVerifyRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Verify a Khalti payment via lookup and activate subscription if Completed.

    Idempotent: re-verifying an already-Completed payment re-activates safely.
    """
    payment, data = await khalti_service.lookup_payment(db, user.id, payload.pidx)

    status_str = data.get("status") or payment.status
    msg = f"Payment status: {status_str}"

    subscription_data = None
    # Only Completed counts as success — per Khalti docs.
    if status_str == "Completed":
        # Activate the paid plan; auto_renew=True for paid subscriptions.
        from app.models.subscription import BillingCycle as BC

        try:
            cycle = BC(payment.billing_cycle)
        except ValueError:
            cycle = BC.MONTHLY
        sub = await subscription_service.activate_subscription(
            db, user.id, billing_cycle=cycle, auto_renew=True
        )
        # Record provider linkage for audit.
        sub.provider = "khalti"
        sub.provider_subscription_id = payment.pidx
        sub.provider_customer_id = payment.transaction_id or payment.tidx
        await db.commit()
        await db.refresh(sub)
        subscription_data = {
            "plan_type": sub.plan_type,
            "billing_cycle": sub.billing_cycle,
            "status": sub.status,
            "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
        }
        msg = "Payment verified — Mentora Pro activated!"
    elif status_str in ("Pending", "Initiated"):
        msg = "Payment is still pending. Please complete it or try again."
    elif status_str in ("User canceled", "Expired"):
        msg = f"Payment {status_str.lower()}. No charge was made."
    elif status_str in ("Refunded", "Partially Refunded"):
        msg = "Payment was refunded."

    return KhaltiVerifyResponse(
        pidx=payment.pidx,
        status=status_str,
        transaction_id=payment.transaction_id,
        total_amount=payment.total_amount or payment.amount,
        fee=payment.fee,
        refunded=data.get("refunded"),
        purchase_order_id=payment.purchase_order_id,
        billing_cycle=payment.billing_cycle,
        subscription=subscription_data,
        message=msg,
    )


@khalti_router.get("/lookup", response_model=KhaltiVerifyResponse)
async def khalti_lookup_get(
    pidx: str = Query(..., description="Payment pidx from Khalti"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """GET convenience wrapper for lookup (useful for return_url redirects)."""
    return await khalti_verify(
        KhaltiVerifyRequest(pidx=pidx), db=db, user=user
    )


@khalti_router.get("/payments", response_model=List[PaymentOut])
async def khalti_list_payments(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List the authenticated user's recent Khalti payments."""
    return await khalti_service.list_user_payments(db, user.id, limit=limit)


@khalti_router.get("/config")
async def khalti_config():
    """Public config to drive the frontend (prices, return URL, enabled flag)."""
    enabled = bool(settings.KHALTI_SECRET_KEY)
    return {
        "enabled": enabled,
        "base_url": settings.KHALTI_BASE_URL,
        "website_url": settings.KHALTI_WEBSITE_URL,
        "return_url": settings.KHALTI_RETURN_URL,
        "prices": {
            "monthly_paisa": settings.SUBSCRIPTION_PRICE_MONTHLY_PAISE,
            "yearly_paisa": settings.SUBSCRIPTION_PRICE_YEARLY_PAISE,
            "monthly_npr": round(settings.SUBSCRIPTION_PRICE_MONTHLY_PAISE / 100, 2),
            "yearly_npr": round(settings.SUBSCRIPTION_PRICE_YEARLY_PAISE / 100, 2),
            "currency": "NPR",
        },
        "billing_cycles": ["MONTHLY", "YEARLY"],
    }
