"""
MOD-12 — Billing & Subscription. Razorpay is mocked (services/billing.py)
per the build's functional-prototype scope for external integrations —
`create-order` -> `verify` always succeeds for a well-formed mock order,
which is enough to exercise the plan-upgrade flow end to end without a
live merchant account.

Access is granted by `activate_subscription` (services/billing.py), called
from two places: `/webhook` (server-to-server, the source of truth once a
real gateway is wired in) and `/orders/verify` (the client-triggered
reconciliation path this mock's synchronous checkout uses today, and a
manual retry a student can hit if a real webhook is ever delayed). Both
paths are idempotent, so a retried/duplicate call never double-grants.
"""
from typing import Any
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.subscription import (
    PLAN_PRICE_INR,
    CreateOrderRequest,
    CreateOrderResponse,
    SubscriptionOut,
    VerifyPaymentRequest,
)
from app.services.billing import (
    activate_subscription,
    create_order as service_create_order,
    get_or_create_subscription,
    verify_webhook_signature,
)

router = APIRouter()


def _to_out(doc: dict) -> SubscriptionOut:
    return SubscriptionOut(
        id=str(doc["_id"]),
        user_id=doc["user_id"],
        plan=doc["plan"],
        ai_usage_quota=doc["ai_usage_quota"],
        used_this_period=doc["used_this_period"],
        period_started_at=doc["period_started_at"],
        expires_at=doc.get("expires_at"),
        razorpay_order_id=doc.get("razorpay_order_id"),
        status=doc["status"],
    )


@router.get("/me", response_model=SubscriptionOut)
async def my_subscription(
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    sub = await get_or_create_subscription(db, str(user["_id"]))
    return _to_out(sub)


@router.post("/orders", response_model=CreateOrderResponse)
async def create_order(
    payload: CreateOrderRequest,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    amount = PLAN_PRICE_INR[payload.plan]
    notes = {"user_id": str(user["_id"]), "plan": payload.plan.value}
    order_id = service_create_order(amount, notes=notes)
    is_mock = order_id.startswith("order_mock_")
    
    # Stash the ordered plan on the subscription doc so /orders/verify knows what to activate
    await get_or_create_subscription(db, str(user["_id"]))
    await db.subscriptions.update_one(
        {"user_id": str(user["_id"])},
        {"$set": {"razorpay_order_id": order_id, "pending_plan": payload.plan.value, "status": "pending_payment"}},
    )
    return CreateOrderResponse(
        order_id=order_id,
        amount_inr=amount,
        plan=payload.plan,
        key_id=None if is_mock else settings.razorpay_key_id,
        mock=is_mock,
    )


@router.post("/orders/verify", response_model=SubscriptionOut)
async def verify_order(
    payload: VerifyPaymentRequest,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Client-triggered reconciliation: accepts order_id, razorpay_payment_id,
    and razorpay_signature. Ownership is verified before subscription activation.
    """
    sub = await db.subscriptions.find_one({"user_id": str(user["_id"])})
    if not sub or sub.get("razorpay_order_id") != payload.order_id:
        raise HTTPException(400, "Order does not match this user's pending order")
    updated = await activate_subscription(
        db,
        payload.order_id,
        payment_id=payload.razorpay_payment_id,
        signature=payload.razorpay_signature,
    )
    return _to_out(updated)


@router.post("/webhook", response_model=SubscriptionOut)
async def payment_webhook(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Server-to-server confirmation for Razorpay Webhooks.
    Validates HMAC signature if X-Razorpay-Signature header is provided.
    """
    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature") or request.headers.get("x-razorpay-signature")
    
    if signature and not verify_webhook_signature(raw_body, signature):
        raise HTTPException(400, "Invalid webhook signature")

    try:
        data = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON payload")

    # Support standard Razorpay webhook structure as well as simple mock structure
    order_id = None
    payment_id = None
    
    if "event" in data and "payload" in data:
        payment_entity = data.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = payment_entity.get("order_id")
        payment_id = payment_entity.get("id")
        if data.get("event") not in ["payment.captured", "order.paid"]:
            raise HTTPException(400, f"Unhandled webhook event: {data.get('event')}")
    else:
        order_id = data.get("order_id")
        if data.get("status") != "success":
            raise HTTPException(402, "Payment not successful")

    if not order_id:
        raise HTTPException(400, "Missing order_id in webhook payload")

    updated = await activate_subscription(db, order_id, payment_id=payment_id)
    return _to_out(updated)
