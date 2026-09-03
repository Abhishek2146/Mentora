"""
Subscription and usage tracking models.
"""

from datetime import date, datetime, timezone
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import BaseModel


# --------------------------------------------------
# Enums
# --------------------------------------------------

class PlanType(str, Enum):
    """Available subscription plan types."""

    FREE = "FREE"
    SUBSCRIPTION = "SUBSCRIPTION"


class BillingCycle(str, Enum):
    """Billing cycles. FREE plans always use NONE."""

    NONE = "NONE"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class SubscriptionStatus(str, Enum):
    """Lifecycle status of a subscription."""

    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class UsageType(str, Enum):
    """Trackable feature usage categories."""

    AI_CHAT = "AI_CHAT"
    NOTE_GENERATION = "NOTE_GENERATION"
    QUIZ_GENERATION = "QUIZ_GENERATION"
    FLASHCARD_GENERATION = "FLASHCARD_GENERATION"
    STUDY_PLAN_GENERATION = "STUDY_PLAN_GENERATION"
    CODING_PROBLEM_GENERATION = "CODING_PROBLEM_GENERATION"
    SYLLABUS_ANALYSIS = "SYLLABUS_ANALYSIS"


# --------------------------------------------------
# Validation
# --------------------------------------------------

VALID_PLAN_BILLING_CYCLES = {
    PlanType.FREE: frozenset({BillingCycle.NONE}),
    PlanType.SUBSCRIPTION: frozenset({BillingCycle.MONTHLY, BillingCycle.YEARLY}),
}


def validate_plan_cycle(plan_type, billing_cycle) -> None:
    """
    Ensure a valid plan/billing-cycle combination.

    Raises ValueError for invalid combinations:
      - FREE must use BillingCycle.NONE
      - SUBSCRIPTION must use MONTHLY or YEARLY
    """

    plan = plan_type if isinstance(plan_type, PlanType) else PlanType(plan_type)
    cycle = (
        billing_cycle
        if isinstance(billing_cycle, BillingCycle)
        else BillingCycle(billing_cycle)
    )

    if cycle not in VALID_PLAN_BILLING_CYCLES[plan]:
        raise ValueError(
            f"Invalid plan/billing-cycle combination: "
            f"plan_type={plan.value} cannot be paired with "
            f"billing_cycle={cycle.value}"
        )


# --------------------------------------------------
# Subscription Model
# --------------------------------------------------

class Subscription(BaseModel):
    """
    Per-user subscription state.

    One row per user (unique user_id). Payment-provider fields are
    placeholders for a future payment integration; no card/payment
    data is ever stored.
    """

    __tablename__ = "subscriptions"

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )

    plan_type = Column(
        String(20),
        default=PlanType.SUBSCRIPTION.value,
        nullable=False,
    )

    billing_cycle = Column(
        String(20),
        default=BillingCycle.MONTHLY.value,
        nullable=False,
    )

    status = Column(
        String(20),
        default=SubscriptionStatus.ACTIVE.value,
        nullable=False,
    )

    started_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    auto_renew = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Future payment-provider linkage (e.g. Stripe). Never store card data.
    provider = Column(String(50), nullable=True)
    provider_customer_id = Column(String(255), nullable=True)
    provider_subscription_id = Column(String(255), nullable=True)

    user = relationship(
        "User",
        back_populates="subscription",
    )

    __table_args__ = (
        CheckConstraint(
            "plan_type IN ('FREE', 'SUBSCRIPTION')",
            name="ck_subscriptions_plan_type",
        ),
        CheckConstraint(
            "(plan_type = 'FREE' AND billing_cycle = 'NONE') OR "
            "(plan_type = 'SUBSCRIPTION' AND "
            "billing_cycle IN ('MONTHLY', 'YEARLY'))",
            name="ck_subscriptions_plan_cycle",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'EXPIRED', 'CANCELLED')",
            name="ck_subscriptions_status",
        ),
    )

    @classmethod
    def create_default(cls, user_id: int) -> "Subscription":
        """Default Mentora Pro subscription for new users."""
        return cls(
            user_id=user_id,
            plan_type=PlanType.SUBSCRIPTION.value,
            billing_cycle=BillingCycle.MONTHLY.value,
            status=SubscriptionStatus.ACTIVE.value,
        )

    def __repr__(self) -> str:
        return (
            f"<Subscription user_id={self.user_id} plan={self.plan_type} "
            f"cycle={self.billing_cycle} status={self.status} "
            f"expires_at={self.expires_at}>"
        )


# --------------------------------------------------
# Usage Model
# --------------------------------------------------

class Usage(BaseModel):
    """
    Daily per-feature usage counter.

    One row per (user_id, usage_type, usage_date). The unique
    constraint guarantees counters cannot be duplicated, and the
    UTC usage_date means daily quotas naturally reset at midnight
    UTC without a cron job.
    """

    __tablename__ = "usage"

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    usage_type = Column(
        String(50),
        nullable=False,
    )

    usage_date = Column(
        Date,
        nullable=False,
        # Defaults to today's UTC date so daily buckets reset naturally.
        default=lambda: datetime.now(timezone.utc).date(),
    )

    request_count = Column(
        Integer,
        default=0,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "usage_type",
            "usage_date",
            name="uq_usage_user_type_date",
        ),
        Index("ix_usage_user_date", "user_id", "usage_date"),
        Index("ix_usage_type", "usage_type"),
    )
