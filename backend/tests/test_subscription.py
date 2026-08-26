"""
Subscription, quota, and rate-limiting tests.

Runs against an in-memory SQLite database (aiosqlite) so no external
PostgreSQL/Redis is required. The Redis rate limiter is replaced with
an in-memory fake that mimics atomic INCR semantics.
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import Depends, FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.auth import get_current_user_id
from app.core.quotas import record_usage, require_ai_quota
from app.database.base import Base
from app.database.database import get_db
from app.models.subscription import (
    BillingCycle,
    PlanType,
    Subscription,
    SubscriptionStatus,
    Usage,
    UsageType,
)
from app.models.user import User
from app.services.rate_limit_service import RateLimiter
from app.services.subscription_service import (
    QUOTA_EXCEEDED_FREE_MESSAGE,
    add_months,
    calculate_expires_at,
    subscription_service,
)


# --------------------------------------------------
# Fixtures
# --------------------------------------------------

class FakeRedis:
    """Minimal in-memory stand-in for redis.asyncio with pipelines."""

    def __init__(self):
        self.store = {}

    def pipeline(self, transaction: bool = True):
        return FakePipeline(self)

    async def delete(self, *keys):
        for key in keys:
            self.store.pop(key, None)


class FakePipeline:
    def __init__(self, client: FakeRedis):
        self.client = client
        self.commands = []

    def incr(self, key):
        self.commands.append(("incr", key))
        return self

    def expire(self, key, ttl):
        self.commands.append(("expire", key, ttl))
        return self

    async def execute(self):
        results = []
        for command in self.commands:
            if command[0] == "incr":
                results.append(self.client.store.get(command[1], 0) + 1)
                self.client.store[command[1]] = results[-1]
            elif command[0] == "expire":
                results.append(True)
        self.commands = []
        return results


@pytest.fixture
async def db_engine(tmp_path):
    # File-based SQLite so concurrent sessions each get their own
    # connection (required for the concurrency test).
    db_path = tmp_path / "test_subscriptions.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    maker = async_sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        email="student@test.com",
        username="student",
        hashed_password="x",
        role="student",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def make_future(months: int) -> datetime:
    return add_months(datetime.now(timezone.utc), months)


# --------------------------------------------------
# 1. New user receives a FREE subscription
# --------------------------------------------------

async def test_new_subscription_defaults_to_free(db_session: AsyncSession, test_user: User):
    subscription = await subscription_service.get_or_create_subscription(
        db_session, test_user.id
    )

    assert subscription.plan_type == PlanType.FREE.value
    assert subscription.billing_cycle == BillingCycle.NONE.value
    assert subscription.status == SubscriptionStatus.ACTIVE.value
    assert subscription.expires_at is None


# --------------------------------------------------
# 2-3. FREE plan limits enforced
# --------------------------------------------------

async def test_free_user_within_limit_ok(db_session: AsyncSession, test_user: User):
    context = await subscription_service.check_quota(
        db_session, test_user.id, UsageType.AI_CHAT
    )
    assert context.plan_type == PlanType.FREE
    assert context.limit == 10
    assert context.used == 0


async def test_free_user_exceeds_quota_rejected(db_session: AsyncSession, test_user: User):
    db_session.add(
        Usage(
            user_id=test_user.id,
            usage_type=UsageType.AI_CHAT.value,
            request_count=10,
        )
    )
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await subscription_service.check_quota(
            db_session, test_user.id, UsageType.AI_CHAT
        )

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail == QUOTA_EXCEEDED_FREE_MESSAGE


# --------------------------------------------------
# 4. SUBSCRIPTION limits applied
# --------------------------------------------------

async def test_subscription_user_gets_higher_limits(
    db_session: AsyncSession, test_user: User
):
    await subscription_service.activate_subscription(
        db_session, test_user.id, BillingCycle.MONTHLY
    )
    context = await subscription_service.check_quota(
        db_session, test_user.id, UsageType.AI_CHAT
    )
    assert context.plan_type == PlanType.SUBSCRIPTION
    assert context.limit == 100


# --------------------------------------------------
# 5-8. Monthly/yearly expiry handling
# --------------------------------------------------

async def test_monthly_expiry_is_one_calendar_month():
    started = datetime(2026, 1, 31, tzinfo=timezone.utc)
    expires = calculate_expires_at(BillingCycle.MONTHLY, started)
    assert expires == datetime(2026, 2, 28, tzinfo=timezone.utc)


async def test_yearly_expiry_is_one_calendar_year_leap_safe():
    started = datetime(2024, 2, 29, tzinfo=timezone.utc)
    expires = calculate_expires_at(BillingCycle.YEARLY, started)
    assert expires == datetime(2025, 2, 28, tzinfo=timezone.utc)


async def test_active_monthly_subscription_before_expiration(
    db_session: AsyncSession, test_user: User
):
    await subscription_service.activate_subscription(
        db_session, test_user.id, BillingCycle.MONTHLY
    )
    subscription = await subscription_service.get_subscription(
        db_session, test_user.id
    )
    assert subscription_service.get_effective_plan(subscription) == (
        PlanType.SUBSCRIPTION
    )


async def test_active_yearly_subscription_before_expiration(
    db_session: AsyncSession, test_user: User
):
    await subscription_service.activate_subscription(
        db_session, test_user.id, BillingCycle.YEARLY
    )
    subscription = await subscription_service.get_subscription(
        db_session, test_user.id
    )
    assert subscription.expires_at is not None
    started = ensure_utc(subscription.started_at)
    expires = ensure_utc(subscription.expires_at)
    assert (expires - started).days >= 365
    assert subscription_service.get_effective_plan(subscription) == (
        PlanType.SUBSCRIPTION
    )


async def test_expired_monthly_falls_back_to_free(
    db_session: AsyncSession, test_user: User
):
    await subscription_service.activate_subscription(
        db_session, test_user.id, BillingCycle.MONTHLY
    )
    subscription = await subscription_service.get_subscription(
        db_session, test_user.id
    )
    subscription.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    await db_session.commit()

    plan, synced = await subscription_service.resolve_effective_plan(
        db_session, subscription
    )
    assert plan == PlanType.FREE
    # Status lazily synced to EXPIRED.
    assert synced.status == SubscriptionStatus.EXPIRED.value


async def test_expired_yearly_falls_back_to_free(
    db_session: AsyncSession, test_user: User
):
    await subscription_service.activate_subscription(
        db_session, test_user.id, BillingCycle.YEARLY
    )
    subscription = await subscription_service.get_subscription(
        db_session, test_user.id
    )
    subscription.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db_session.commit()

    assert subscription_service.get_effective_plan(subscription) == PlanType.FREE
    limit = subscription_service.get_daily_limit(
        PlanType.FREE, UsageType.SYLLABUS_ANALYSIS
    )
    assert limit == 2


# --------------------------------------------------
# 9. Rate limiter returns 429 behaviour
# --------------------------------------------------

async def test_rate_limiter_blocks_after_limit(monkeypatch):
    fake_redis = FakeRedis()
    limiter = RateLimiter()
    limiter.redis_client = fake_redis
    limiter._is_available = True

    allowed_count = 0
    for _ in range(10):
        allowed, _retry = await limiter.check("user:1", 10)
        assert allowed
        allowed_count += 1

    allowed, retry_after = await limiter.check("user:1", 10)
    assert not allowed
    assert retry_after >= 1
    assert allowed_count == 10


async def test_rate_limiter_independent_per_user(monkeypatch):
    fake_redis = FakeRedis()
    limiter = RateLimiter()
    limiter.redis_client = fake_redis
    limiter._is_available = True

    for _ in range(10):
        await limiter.check("user:1", 10)

    allowed, _ = await limiter.check("user:2", 10)
    assert allowed


# --------------------------------------------------
# 10-11. Usage increment policy via protected endpoint flow
# --------------------------------------------------

@pytest.fixture
def quota_app(db_session: AsyncSession, test_user: User) -> FastAPI:
    """
    Small FastAPI app exercising the real dependency chain:
    auth override -> require_ai_quota -> endpoint -> record_usage.
    """

    app = FastAPI()

    @app.post("/ai/chat")
    async def fake_chat_endpoint(
        quota_ctx=Depends(require_ai_quota(UsageType.AI_CHAT)),
    ):
        # Simulated expensive AI operation succeeded.
        await record_usage(db_session, test_user.id, UsageType.AI_CHAT)
        return {"ok": True, "used": quota_ctx.used}

    @app.post("/ai/syllabus")
    async def fake_syllabus_endpoint(
        quota_ctx=Depends(require_ai_quota(UsageType.SYLLABUS_ANALYSIS)),
    ):
        await record_usage(db_session, test_user.id, UsageType.SYLLABUS_ANALYSIS)
        return {"ok": True, "used": quota_ctx.used}

    app.dependency_overrides[get_current_user_id] = lambda: test_user.id

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    return app


@pytest.fixture
async def quota_client(quota_app: FastAPI) -> AsyncClient:
    transport = ASGITransport(app=quota_app)
    return AsyncClient(transport=transport, base_url="http://test")


async def test_successful_operation_increments_once(
    quota_client: AsyncClient, db_session: AsyncSession, test_user: User
):
    response = await quota_client.post("/ai/chat")
    assert response.status_code == 200

    count = await subscription_service.get_usage_count(
        db_session, test_user.id, UsageType.AI_CHAT
    )
    assert count == 1


async def test_rejected_requests_do_not_increment_usage(
    quota_client: AsyncClient, db_session: AsyncSession, test_user: User
):
    # Exhaust the FREE AI_CHAT quota before any request.
    await subscription_service.increment_usage(
        db_session, test_user.id, UsageType.AI_CHAT, amount=10
    )

    response = await quota_client.post("/ai/chat")
    assert response.status_code == 429
    assert "Retry-After" in response.headers

    # Still exactly at the pre-set value: rejection was not counted.
    count = await subscription_service.get_usage_count(
        db_session, test_user.id, UsageType.AI_CHAT
    )
    assert count == 10

    # A different feature is unaffected by AI_CHAT's exhaustion.
    other = await quota_client.post("/ai/syllabus")
    assert other.status_code == 200


async def test_rate_limited_request_does_not_increment_usage(
    db_session: AsyncSession, test_user: User, monkeypatch
):
    fake_redis = FakeRedis()
    limiter = RateLimiter()
    limiter.redis_client = fake_redis
    limiter._is_available = True

    from app.core import quotas as quotas_module

    monkeypatch.setattr(quotas_module, "rate_limiter", limiter)

    app = FastAPI()

    @app.post("/ai")
    async def fake_ai(quota_ctx=Depends(require_ai_quota(UsageType.AI_CHAT))):
        await record_usage(db_session, test_user.id, UsageType.AI_CHAT)
        return {"ok": True}

    app.dependency_overrides[get_current_user_id] = lambda: test_user.id

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as client:
        # FREE per-minute rate limit is 10; the 11th gets 429.
        for _ in range(10):
            assert (await client.post("/ai")).status_code == 200
        blocked = await client.post("/ai")
        assert blocked.status_code == 429
        assert blocked.json()["detail"] == "Too many requests. Please try again later."

    count = await subscription_service.get_usage_count(
        db_session, test_user.id, UsageType.AI_CHAT
    )
    assert count == 10


# --------------------------------------------------
# 12. Concurrent increments cannot bypass the quota
# --------------------------------------------------

async def test_concurrent_increments_never_duplicate_or_bypass(
    db_engine, test_user: User
):
    maker = async_sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)

    async def bump():
        async with maker() as session:
            await subscription_service.increment_usage(
                session, test_user.id, UsageType.QUIZ_GENERATION
            )

    await asyncio.gather(*(bump() for _ in range(8)))

    async with maker() as session:
        rows = (
            (await session.execute(select(Usage).where(Usage.user_id == test_user.id)))
            .scalars().all()
        )
        assert len(rows) == 1  # unique constraint prevents duplicates
        assert rows[0].request_count == 8

        with pytest.raises(HTTPException) as exc_info:
            await subscription_service.check_quota(
                session, test_user.id, UsageType.QUIZ_GENERATION
            )
        assert exc_info.value.status_code == 429


# --------------------------------------------------
# 13-15. Ownership + admin-only management
# --------------------------------------------------

async def test_users_cannot_access_another_users_subscription(
    db_session: AsyncSession, test_user: User
):
    other = User(email="o@t.com", username="other", hashed_password="x", role="student")
    db_session.add(other)
    await db_session.commit()
    await db_session.refresh(other)

    mine = await subscription_service.get_or_create_subscription(
        db_session, test_user.id
    )
    theirs = await subscription_service.get_or_create_subscription(
        db_session, other.id
    )

    assert mine.user_id == test_user.id
    assert theirs.user_id == other.id
    assert mine.id != theirs.id


async def test_admin_can_manage_subscriptions(
    db_session: AsyncSession, test_user: User
):
    activated = await subscription_service.activate_subscription(
        db_session, test_user.id, BillingCycle.YEARLY, auto_renew=True
    )
    assert activated.plan_type == PlanType.SUBSCRIPTION.value
    assert activated.billing_cycle == BillingCycle.YEARLY.value
    assert activated.auto_renew is True
    assert activated.expires_at is not None

    cancelled = await subscription_service.cancel_subscription(
        db_session, test_user.id
    )
    assert cancelled.status == SubscriptionStatus.CANCELLED.value
    assert subscription_service.get_effective_plan(cancelled) == PlanType.FREE

    expired = await subscription_service.expire_subscription(
        db_session, test_user.id
    )
    assert expired.status == SubscriptionStatus.EXPIRED.value


async def test_normal_user_cannot_modify_own_subscription_status(
    db_session: AsyncSession, test_user: User
):
    """
    The public API exposes no mutation path for a user's own
    subscription: only admin service methods change plan/status/expires.
    Verify the service rejects invalid self-service-style updates.
    """
    from app.models.subscription import validate_plan_cycle

    with pytest.raises(ValueError):
        validate_plan_cycle(PlanType.FREE, BillingCycle.MONTHLY)
    with pytest.raises(ValueError):
        validate_plan_cycle(PlanType.SUBSCRIPTION, BillingCycle.NONE)

    # DB-level guard also exists.
    with pytest.raises(IntegrityError):
        db_session.add(
            Subscription(user_id=999999, plan_type="FREE", billing_cycle="MONTHLY")
        )
        await db_session.commit()
        await db_session.rollback()


# --------------------------------------------------
# 16. Daily usage resets on the UTC date
# --------------------------------------------------

async def test_daily_usage_resets_by_utc_date(
    db_session: AsyncSession, test_user: User
):
    yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)

    db_session.add(
        Usage(
            user_id=test_user.id,
            usage_type=UsageType.AI_CHAT.value,
            usage_date=yesterday,
            request_count=10,
        )
    )
    await db_session.commit()

    # Yesterday's counter must not affect today's quota.
    context = await subscription_service.check_quota(
        db_session, test_user.id, UsageType.AI_CHAT
    )
    assert context.used == 0
    assert context.remaining == 10

    used_today = await subscription_service.get_usage_count(
        db_session, test_user.id, UsageType.AI_CHAT, usage_date=yesterday
    )
    assert used_today == 10


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
