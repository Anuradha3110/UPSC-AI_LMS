"""
subscriptions collection (§07) — MOD-12. Razorpay is mocked for this
build (a sandbox order/verify flow, not a live merchant account) per
the build decision to keep infra-heavy externals functional-but-mocked;
swap `services/billing.py`'s two functions for real Razorpay SDK calls
when a live account exists — the rest of the module doesn't change.
"""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class PlanTier(str, Enum):
    free_diagnostic = "free_diagnostic"
    prelims_only = "prelims_only"
    full_prep = "full_prep"  # Prelims + Mains + Interview


PLAN_AI_QUOTAS = {
    # answers graded per 30-day period — enforced in the orchestration layer (§09)
    PlanTier.free_diagnostic: 3,
    PlanTier.prelims_only: 10,
    PlanTier.full_prep: 100,
}

PLAN_PRICE_INR = {
    PlanTier.free_diagnostic: 0,
    PlanTier.prelims_only: 499,
    PlanTier.full_prep: 999,
}

# Paid plans grant access for one billing period; free_diagnostic never expires.
PLAN_PERIOD_DAYS = 30


class SubscriptionOut(BaseModel):
    id: str
    user_id: str
    plan: PlanTier
    ai_usage_quota: int
    used_this_period: int
    period_started_at: datetime
    expires_at: datetime | None = None
    razorpay_order_id: str | None = None
    status: str  # "active" | "pending_payment" | "expired"


class CreateOrderRequest(BaseModel):
    plan: PlanTier


class CreateOrderResponse(BaseModel):
    order_id: str
    amount_inr: int
    plan: PlanTier
    key_id: str | None = None
    mock: bool = True


class VerifyPaymentRequest(BaseModel):
    order_id: str
    razorpay_payment_id: str | None = None
    razorpay_signature: str | None = None
