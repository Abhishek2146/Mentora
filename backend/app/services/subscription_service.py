"""
Subscription and usage-quota service.

All plan-resolution, expiration, quota, and usage-counting logic is
centralized here so endpoints never implement per-plan checks
themselves.
"""

import calendar
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.subscription import (
    BillingCycle,
    PlanType,
    Subscription,
    SubscriptionStatus,
    Usage,
    UsageType,
    validate_plan_cycle,
)

logger = logging.getLogger(__name__)

# --------------------------------------------------
# Error messages (single source of truth)
# --------------------------------------------------

RATE_LIMIT_MESSAGE = "Too many requests. Please try again later."
QUOTA_EXCEEDED_FREE_MESSAGE = (
    "Daily usage limit reached. Please try again tomorrow or subscribe "
    "to Mentora."
)
QUOTA_EXCEEDED_SUBSCRIPTION_MESSAGE = (
    "You have reached your daily limit for this feature."
)


# --------------------------------------------------
# Time helpers (UTC everywhere)
# --------------------------------------------------

def utc_now() -> datetime:
    """Current time as timezone-aware UTC."""
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    """Normalize a possibly-naive datetime to UTC-aware."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def today_utc() -> date:
    return utc_now().date()


def seconds_until_next_utc_midnight() -> int:
    """Retry-After hint for daily-quota rejections."""
    now = utc_now()
    next_midnight = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return max(1, int((next_midnight - now).total_seconds()))


# --------------------------------------------------
# Calendar-aware expiry calculation
# --------------------------------------------------

def add_months(start: datetime, months: int) -> datetime:
    """
    Add calendar months, clamping the day when the target month is
    shorter (e.g. Jan 31 + 1 month -> Feb 28/29; Feb 29 2024 + 1 year
    -> Feb 28 2025).
    """

    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return start.replace(year=year, month=month, day=day)


def calculate_expires_at(
    billing_cycle,
    started_at: datetime,
) -> Optional[datetime]:
    """
    Compute expires_at for a billing cycle.

    MONTHLY -> one calendar month from started_at
    YEARLY  -> one calendar year from started_at
    NONE/unknown -> None
    """

    cycle = (
        billing_cycle
        if isinstance(billing_cycle, BillingCycle)
        else BillingCycle(billing_cycle)
    )
    started = ensure_utc(started_at)

    if cycle == BillingCycle.MONTHLY:
        return add_months(started, 1)
    if cycle == BillingCycle.YEARLY:
        return add_months(started, 12)
    return None


# --------------------------------------------------
# Quota context
# --------------------------------------------------

@dataclass
class QuotaContext:
    """Result of a successful quota check, returned to endpoints."""

    user_id: int
    plan_type: PlanType
    billing_cycle: BillingCycle
    status: SubscriptionStatus
    subscription: Subscription
    used: int
    limit: int

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.used)


# --------------------------------------------------
# Service
# --------------------------------------------------

class SubscriptionService:
    """Centralized subscription, plan-limit and usage logic."""

    # --------------------------------------------------
    # Subscription lookup
    # --------------------------------------------------

    async def get_subscription(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> Optional[Subscription]:
        result = await db.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        return result.scalars().first()

    async def get_or_create_subscription(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> Subscription:
        """
        Fetch the user's subscription, creating a default Mentora Pro
        one on first access. Safe against concurrent creation thanks to
        the unique user_id constraint.
        """

        subscription = await self.get_subscription(db, user_id)
        if subscription is not None:
            return subscription

        subscription = Subscription.create_default(user_id)
        db.add(subscription)
        try:
            await db.commit()
        except IntegrityError:
            # Another request created it concurrently.
            await db.rollback()
            subscription = await self.get_subscription(db, user_id)
            if subscription is None:
                raise
            return subscription

        await db.refresh(subscription)
        logger.info("Created default Mentora Pro subscription for user %s", user_id)
        return subscription

    # --------------------------------------------------
    # Effective plan / expiry enforcement
    # --------------------------------------------------

    def get_effective_plan(self, subscription: Subscription) -> PlanType:
        """
        The plan whose limits currently apply.

        Expired or cancelled SUBSCRIPTION plans automatically fall back
        to FREE — no manual database update is ever required to enforce
        expiration.
        """

        plan = PlanType(subscription.plan_type)

        if plan != PlanType.SUBSCRIPTION:
            return PlanType.FREE

        state = SubscriptionStatus(subscription.status)
        if state != SubscriptionStatus.ACTIVE:
            return PlanType.FREE

        expires_at = subscription.expires_at
        if expires_at is not None and ensure_utc(expires_at) <= utc_now():
            return PlanType.FREE

        return PlanType.SUBSCRIPTION

    async def resolve_effective_plan(
        self,
        db: AsyncSession,
        subscription: Subscription,
    ) -> Tuple[PlanType, Subscription]:
        """
        Resolve the effective plan and lazily sync an expired database
        row to EXPIRED status (best-effort bookkeeping only — benefit
        loss does not depend on this write).
        """

        plan = self.get_effective_plan(subscription)

        if (
            plan == PlanType.FREE
            and PlanType(subscription.plan_type) == PlanType.SUBSCRIPTION
            and SubscriptionStatus(subscription.status)
            == SubscriptionStatus.ACTIVE
        ):
            subscription.status = SubscriptionStatus.EXPIRED.value
            try:
                await db.commit()
                logger.info(
                    "Subscription for user %s marked EXPIRED",
                    subscription.user_id,
                )
            except Exception:
                await db.rollback()

        return plan, subscription

    def is_expired(self, subscription: Subscription) -> bool:
        """True when an ACTIVE subscription's expires_at has passed."""
        expires_at = subscription.expires_at
        return (
            SubscriptionStatus(subscription.status) == SubscriptionStatus.ACTIVE
            and expires_at is not None
            and ensure_utc(expires_at) <= utc_now()
        )

    # --------------------------------------------------
    # Configured limits
    # --------------------------------------------------

    def get_daily_limit(
        self,
        plan_type: PlanType,
        usage_type: UsageType,
    ) -> int:
        """Configured daily quota for a plan/feature. 0 means blocked."""
        limits = (
            settings.SUBSCRIPTION_DAILY_LIMITS
            if plan_type == PlanType.SUBSCRIPTION
            else settings.FREE_DAILY_LIMITS
        )
        return int(limits.get(usage_type.value, 0))

    def get_rate_limit(self, plan_type: PlanType) -> int:
        """Configured requests-per-minute for a plan."""
        if plan_type == PlanType.SUBSCRIPTION:
            return settings.RATE_LIMIT_SUBSCRIPTION_PER_MINUTE
        return settings.RATE_LIMIT_FREE_PER_MINUTE

    # --------------------------------------------------
    # Usage counting (UTC day buckets)
    # --------------------------------------------------

    async def get_usage_row(
        self,
        db: AsyncSession,
        user_id: int,
        usage_type: UsageType,
        usage_date: Optional[date] = None,
    ) -> Optional[Usage]:
        result = await db.execute(
            select(Usage).where(
                Usage.user_id == user_id,
                Usage.usage_type == usage_type.value,
                Usage.usage_date == (usage_date or today_utc()),
            )
        )
        return result.scalars().first()

    async def get_usage_count(
        self,
        db: AsyncSession,
        user_id: int,
        usage_type: UsageType,
        usage_date: Optional[date] = None,
    ) -> int:
        usage = await self.get_usage_row(db, user_id, usage_type, usage_date)
        return usage.request_count if usage else 0

    async def increment_usage(
        self,
        db: AsyncSession,
        user_id: int,
        usage_type: UsageType,
        amount: int = 1,
    ) -> Usage:
        """
        Increment today's usage counter for a feature.

        Call ONLY after the AI operation has been accepted/executed so
        rejected requests are never counted. The unique constraint on
        (user_id, usage_type, usage_date) prevents duplicate rows under
        concurrency.
        """

        usage_date = today_utc()

        # Atomic server-side increment: concurrent requests can never
        # overwrite each other's count (no lost updates).
        result = await db.execute(
            update(Usage)
            .where(
                Usage.user_id == user_id,
                Usage.usage_type == usage_type.value,
                Usage.usage_date == usage_date,
            )
            .values(request_count=Usage.request_count + amount)
        )

        if result.rowcount == 0:
            # First use today — create the row.
            usage = Usage(
                user_id=user_id,
                usage_type=usage_type.value,
                usage_date=usage_date,
                request_count=amount,
            )
            db.add(usage)
            try:
                await db.flush()
            except IntegrityError:
                # Lost a race to create the row — retry atomically.
                await db.rollback()
                await db.execute(
                    update(Usage)
                    .where(
                        Usage.user_id == user_id,
                        Usage.usage_type == usage_type.value,
                        Usage.usage_date == usage_date,
                    )
                    .values(request_count=Usage.request_count + amount)
                )
                return await self.get_usage_row(db, user_id, usage_type, usage_date)
        else:
            usage = await self.get_usage_row(db, user_id, usage_type, usage_date)

        await db.commit()
        await db.refresh(usage)
        return usage

    # --------------------------------------------------
    # Quota checking
    # --------------------------------------------------

    async def check_quota(
        self,
        db: AsyncSession,
        user_id: int,
        usage_type: UsageType,
        subscription: Optional[Subscription] = None,
        effective_plan: Optional[PlanType] = None,
    ) -> QuotaContext:
        """
        Verify the user may still perform a feature today.

        Raises HTTP 429 with a plan-appropriate message when the daily
        quota is exhausted. Returns a QuotaContext on success.
        """

        if subscription is None:
            subscription = await self.get_or_create_subscription(
                db, user_id
            )

        if effective_plan is None:
            effective_plan, subscription = await self.resolve_effective_plan(
                db, subscription
            )

        used = await self.get_usage_count(db, user_id, usage_type)
        limit = self.get_daily_limit(effective_plan, usage_type)

        context = QuotaContext(
            user_id=user_id,
            plan_type=effective_plan,
            billing_cycle=BillingCycle(subscription.billing_cycle),
            status=SubscriptionStatus(subscription.status),
            subscription=subscription,
            used=used,
            limit=limit,
        )

        if settings.QUOTA_ENABLED and used >= limit:
            detail = (
                QUOTA_EXCEEDED_FREE_MESSAGE
                if effective_plan == PlanType.FREE
                else QUOTA_EXCEEDED_SUBSCRIPTION_MESSAGE
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=detail,
                headers={
                    "Retry-After": str(seconds_until_next_utc_midnight())
                },
            )

        return context

    # --------------------------------------------------
    # Admin mutations
    # --------------------------------------------------

    async def activate_subscription(
        self,
        db: AsyncSession,
        user_id: int,
        billing_cycle,
        auto_renew: bool = False,
    ) -> Subscription:
        """Activate a paid subscription (admin/payment-provider path)."""

        cycle = (
            billing_cycle
            if isinstance(billing_cycle, BillingCycle)
            else BillingCycle(billing_cycle)
        )
        validate_plan_cycle(PlanType.SUBSCRIPTION, cycle)

        subscription = await self.get_or_create_subscription(db, user_id)

        started_at = utc_now()
        subscription.plan_type = PlanType.SUBSCRIPTION.value
        subscription.billing_cycle = cycle.value
        subscription.status = SubscriptionStatus.ACTIVE.value
        subscription.started_at = started_at
        subscription.expires_at = calculate_expires_at(cycle, started_at)
        subscription.auto_renew = auto_renew

        await db.commit()
        await db.refresh(subscription)
        logger.info(
            "Activated %s subscription for user %s until %s",
            cycle.value,
            user_id,
            subscription.expires_at,
        )
        return subscription

    async def cancel_subscription(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> Subscription:
        """Cancel immediately — benefits end at once."""
        subscription = await self.get_or_create_subscription(db, user_id)
        subscription.status = SubscriptionStatus.CANCELLED.value
        subscription.auto_renew = False
        await db.commit()
        await db.refresh(subscription)
        return subscription

    async def expire_subscription(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> Subscription:
        """Force-expire a subscription (admin action)."""
        subscription = await self.get_or_create_subscription(db, user_id)
        subscription.expires_at = utc_now()
        subscription.status = SubscriptionStatus.EXPIRED.value
        subscription.auto_renew = False
        await db.commit()
        await db.refresh(subscription)
        return subscription


subscription_service = SubscriptionService()
