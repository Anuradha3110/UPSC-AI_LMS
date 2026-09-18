"""
MOD-12 — Billing & Subscription with Razorpay Payment Gateway integration.
Supports live Razorpay Orders API, checkout signature verification, and
webhook HMAC signature validation, while retaining sandbox mock fallbacks
when Razorpay API credentials are not configured.
"""
import hmac
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
import razorpay

from app.core.config import settings
from app.models.subscription import PLAN_AI_QUOTAS, PLAN_PERIOD_DAYS, PlanTier


def get_razorpay_client() -> razorpay.Client | None:
    key_id = (settings.razorpay_key_id or "").strip("'\" \t\r\n")
    key_secret = (settings.razorpay_key_secret or "").strip("'\" \t\r\n")
    if key_id and key_secret and not key_id.startswith("rzp_test_...") and key_id != "change-me":
        return razorpay.Client(auth=(key_id, key_secret))
    return None


async def get_or_create_subscription(db: AsyncIOMotorDatabase, user_id: str) -> dict:
    sub = await db.subscriptions.find_one({"user_id": user_id})
    if not sub:
        doc = {
            "user_id": user_id,
            "plan": PlanTier.free_diagnostic.value,
            "ai_usage_quota": PLAN_AI_QUOTAS[PlanTier.free_diagnostic],
            "used_this_period": 0,
            "period_started_at": datetime.now(timezone.utc),
            "expires_at": None,
            "razorpay_order_id": None,
            "last_verified_order_id": None,
            "status": "active",
        }
        result = await db.subscriptions.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc
    return await _expire_if_needed(db, sub)


async def _expire_if_needed(db: AsyncIOMotorDatabase, sub: dict) -> dict:
    """A paid plan whose period has lapsed drops back to free_diagnostic
    access — this is what actually revokes access once payment isn't
    current, mirroring `activate_subscription` granting it."""
    expires_at = sub.get("expires_at")
    if expires_at is None or sub["plan"] == PlanTier.free_diagnostic.value:
        return sub
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) < expires_at:
        return sub

    update = {
        "plan": PlanTier.free_diagnostic.value,
        "ai_usage_quota": PLAN_AI_QUOTAS[PlanTier.free_diagnostic],
        "used_this_period": 0,
        "period_started_at": datetime.now(timezone.utc),
        "expires_at": None,
        "status": "active",
    }
    await db.subscriptions.update_one({"_id": sub["_id"]}, {"$set": update})
    sub.update(update)
    return sub


def is_entitled(sub: dict, *allowed_plans: str) -> bool:
    return sub["plan"] in allowed_plans


def create_order(amount_inr: int, notes: dict | None = None) -> str:
    """Create a live Razorpay Order if API credentials are configured,
    otherwise fallback to deterministic sandbox order creation."""
    client = get_razorpay_client()
    if client:
        try:
            data = {
                "amount": amount_inr * 100,  # Razorpay amount is in paise (₹1 = 100 paise)
                "currency": "INR",
                "receipt": f"rcpt_{secrets.token_hex(6)}",
                "notes": notes or {},
            }
            order = client.order.create(data=data)
            return order["id"]
        except Exception as err:
            err_msg = str(err)
            if "Authentication failed" in err_msg or "Unauthorized" in err_msg or "401" in err_msg:
                raise HTTPException(
                    400,
                    "Razorpay Authentication Failed: The RAZORPAY_KEY_ID or RAZORPAY_KEY_SECRET in backend/.env is invalid or rejected by Razorpay. "
                    "Please generate fresh API keys from your Razorpay Dashboard (https://dashboard.razorpay.com/app/keys) and update backend/.env."
                )
            raise HTTPException(500, f"Razorpay order creation failed: {err_msg}")
    return create_mock_order(amount_inr)


def verify_payment_signature(order_id: str, payment_id: str | None = None, signature: str | None = None) -> bool:
    """Verify Razorpay payment signature for live orders, or validate mock order format."""
    if order_id.startswith("order_mock_"):
        return verify_mock_payment(order_id)

    client = get_razorpay_client()
    if client and payment_id and signature:
        try:
            client.utility.verify_payment_signature({
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
            })
            return True
        except razorpay.errors.SignatureVerificationError:
            return False
        except Exception:
            return False
    # If live client not set or missing params, check mock format fallback
    return verify_mock_payment(order_id)


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """Verify HMAC signature for incoming Razorpay webhooks."""
    if settings.razorpay_webhook_secret and signature:
        client = get_razorpay_client()
        if client:
            try:
                client.utility.verify_webhook_signature(
                    body.decode("utf-8"), signature, settings.razorpay_webhook_secret
                )
                return True
            except Exception:
                return False
    return True


async def activate_subscription(
    db: AsyncIOMotorDatabase,
    order_id: str,
    payment_id: str | None = None,
    signature: str | None = None,
) -> dict:
    """Server-side activation, shared by the webhook and client reconciliation call.
    Idempotent: replaying the same order_id does not double-grant quota.
    """
    sub = await db.subscriptions.find_one({"razorpay_order_id": order_id})
    if not sub:
        raise HTTPException(400, "No pending order found for this order_id")
    if sub.get("last_verified_order_id") == order_id and sub["status"] == "active":
        return sub  # already processed — no-op
    if not verify_payment_signature(order_id, payment_id, signature):
        raise HTTPException(402, "Payment verification failed")

    plan = PlanTier(sub["pending_plan"])
    now = datetime.now(timezone.utc)
    update = {
        "plan": plan.value,
        "ai_usage_quota": PLAN_AI_QUOTAS[plan],
        "used_this_period": 0,
        "period_started_at": now,
        "expires_at": None if plan == PlanTier.free_diagnostic else now + timedelta(days=PLAN_PERIOD_DAYS),
        "status": "active",
        "last_verified_order_id": order_id,
    }
    await db.subscriptions.update_one({"_id": sub["_id"]}, {"$set": update})
    sub.update(update)
    return sub


async def check_and_consume_ai_quota(db: AsyncIOMotorDatabase, user_id: str) -> None:
    """Raises 402 if the plan's per-period AI-grading quota is exhausted."""
    sub = await get_or_create_subscription(db, user_id)
    if sub["used_this_period"] >= sub["ai_usage_quota"]:
        raise HTTPException(
            402,
            f"AI grading quota exhausted for the '{sub['plan']}' plan "
            f"({sub['ai_usage_quota']}/period). Upgrade your plan to grade more answers.",
        )
    await db.subscriptions.update_one({"_id": sub["_id"]}, {"$inc": {"used_this_period": 1}})


def create_mock_order(amount_inr: int) -> str:
    return f"order_mock_{secrets.token_hex(8)}"


def verify_mock_payment(order_id: str) -> bool:
    return order_id.startswith("order_mock_")
