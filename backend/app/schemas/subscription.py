"""
Subscription and usage schemas.

User-facing responses intentionally exclude payment-provider fields
(provider, provider_customer_id, provider_subscription_id).
"""

from datetime import date, datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, validator

from app.models.subscription import BillingCycle, PlanType, SubscriptionStatus


# ============================================================
# Plan catalogue
# ============================================================

class PlanInfo(BaseModel):
    """A plan and its configured limits."""

    plan_type: str
    billing_cycles: List[str]
    rate_limit_per_minute: int
    daily_limits: Dict[str, int]
    # Pricing in paisa and NPR (e.g. 99900 paisa = Rs 999). Null for FREE.
    price_monthly_paisa: Optional[int] = None
    price_yearly_paisa: Optional[int] = None
    price_monthly_npr: Optional[float] = None
    price_yearly_npr: Optional[float] = None


class PlansResponse(BaseModel):
    plans: List[PlanInfo]


# ============================================================
# User subscription responses
# ============================================================

class SubscriptionOut(BaseModel):
    """The authenticated user's own subscription (no provider data)."""

    id: int
    user_id: int
    plan_type: PlanType
    billing_cycle: BillingCycle
    status: SubscriptionStatus
    started_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    auto_renew: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FeatureUsageOut(BaseModel):
    """Per-feature usage summary for today (UTC)."""

    usage_type: str
    daily_limit: int
    used: int
    remaining: int
    usage_date: date


class UsageOut(BaseModel):
    """Current usage and remaining quota for the authenticated user."""

    user_id: int
    plan_type: str
    billing_cycle: str
    status: str
    expires_at: Optional[datetime] = None
    effective_plan: str
    rate_limit_per_minute: int
    features: List[FeatureUsageOut]
    usage_date: date


# ============================================================
# Admin management
# ============================================================

class AdminActivateRequest(BaseModel):
    """Admin payload to activate a paid subscription."""

    billing_cycle: BillingCycle
    auto_renew: bool = False

    @validator("billing_cycle")
    def cycle_must_be_paid(cls, value: BillingCycle) -> BillingCycle:
        if value == BillingCycle.NONE:
            raise ValueError(
                "billing_cycle must be MONTHLY or YEARLY"
            )
        return value


class AdminSubscriptionOut(SubscriptionOut):
    """Admin view of a subscription, including provider linkage fields."""

    provider: Optional[str] = None
    provider_customer_id: Optional[str] = None
    provider_subscription_id: Optional[str] = None
