"""
Reusable FastAPI dependencies for AI rate-limiting and quotas.

Endpoints consume AI resources through `require_ai_quota(...)` so no
per-endpoint plan checks are ever written by hand:

    @router.post("/chat")
    async def chat(
        quota: QuotaContext = Depends(require_ai_quota(UsageType.AI_CHAT)),
        ...
    ):
        result = await do_expensive_ai_work(...)
        await record_usage(db, user_id, UsageType.AI_CHAT)
        return result

Usage is only recorded AFTER the expensive operation succeeds, so
authentication/validation/rate-limit/quota rejections never count.
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user_id
from app.core.config import settings
from app.database.database import get_db
from app.models.subscription import UsageType
from app.services.rate_limit_service import RATE_LIMIT_MESSAGE, rate_limiter
from app.services.subscription_service import (
    QuotaContext,
    subscription_service,
)


async def check_rate_limit(
    user_id: int,
    plan_type,
) -> None:
    """
    Per-user Redis request-rate limiting (separate from daily quotas).

    Raises HTTP 429 with a Retry-After header when the plan's
    per-minute request limit is exceeded.
    """

    if not settings.USER_RATE_LIMIT_ENABLED:
        return

    limit = subscription_service.get_rate_limit(plan_type)
    allowed, retry_after = await rate_limiter.check(
        f"user:{user_id}",
        limit,
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=RATE_LIMIT_MESSAGE,
            headers={"Retry-After": str(retry_after)},
        )


def require_ai_quota(usage_type: UsageType):
    """
    Dependency factory protecting AI endpoints.

    Flow (all before the endpoint body runs):
      1. Authenticate the user (existing JWT dependency).
      2. Load/create the user's subscription.
      3. Resolve the effective plan (expired -> FREE).
      4. Enforce the Redis per-minute rate limit for that plan.
      5. Enforce the feature-specific daily quota.

    Returns a QuotaContext describing the resolved limits.
    """

    async def dependency(
        user_id: int = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db),
    ) -> QuotaContext:
        subscription = await subscription_service.get_or_create_subscription(
            db, user_id
        )
        effective_plan, _ = await subscription_service.resolve_effective_plan(
            db, subscription
        )

        # 1. Redis request rate limiting (per-minute window).
        await check_rate_limit(user_id, effective_plan)

        # 2. Feature-specific daily subscription quota.
        context = await subscription_service.check_quota(
            db,
            user_id,
            usage_type,
            subscription=subscription,
            effective_plan=effective_plan,
        )
        return context

    return dependency


async def record_usage(
    db: AsyncSession,
    user_id: int,
    usage_type: UsageType,
) -> None:
    """
    Increment today's usage counter for a feature.

    Must be called only after the AI operation has been successfully
    executed/accepted — never on rejected requests.
    """

    await subscription_service.increment_usage(db, user_id, usage_type)
