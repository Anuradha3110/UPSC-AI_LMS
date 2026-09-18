"""
MOD-10 — Notifications & Engagement, in-app channel. Writes happen from
other routers/background jobs via services/notify.notify(); this router
is purely the aspirant's read/mark-read surface (the bell icon).
"""
from bson import ObjectId
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.notification import NotificationOut

router = APIRouter()


def _to_out(doc: dict) -> NotificationOut:
    return NotificationOut(
        id=str(doc["_id"]),
        user_id=doc["user_id"],
        type=doc["type"],
        title=doc["title"],
        body=doc["body"],
        read=doc.get("read", False),
        created_at=doc["created_at"],
    )


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    unread_only: bool = False,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    query: dict = {"user_id": str(user["_id"])}
    if unread_only:
        query["read"] = False
    docs = await db.notifications.find(query).sort("created_at", -1).limit(100).to_list(length=100)
    return [_to_out(d) for d in docs]


@router.post("/{notification_id}/read", response_model=NotificationOut)
async def mark_read(
    notification_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    await db.notifications.update_one(
        {"_id": ObjectId(notification_id), "user_id": str(user["_id"])},
        {"$set": {"read": True}},
    )
    doc = await db.notifications.find_one({"_id": ObjectId(notification_id)})
    return _to_out(doc)
