"""
MOD-10 — Notifications & Engagement. In-app notifications are real
(written to Mongo, read by the frontend's bell icon). Email/WhatsApp are
stubbed: this function is the one place a real SMTP client or the
WhatsApp Business Cloud API would be called from — right now it just
logs what *would* have been sent, so the notification-triggering logic
elsewhere (revision due, digest ready, mock reminder) doesn't have to
change when a real sender is wired in later.
"""
import logging

from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.notification import NotificationType

logger = logging.getLogger("nirdesh.notify")


async def notify(
    db: AsyncIOMotorDatabase,
    user_id: str,
    type_: NotificationType,
    title: str,
    body: str,
    also_send_external: bool = False,
) -> None:
    doc = {
        "user_id": user_id,
        "type": type_.value,
        "title": title,
        "body": body,
        "read": False,
        "created_at": datetime.now(timezone.utc),
    }
    await db.notifications.insert_one(doc)

    if also_send_external:
        # Real deployment: call an SMTP client and the WhatsApp Business
        # Cloud API here, gated by user notification preferences.
        logger.info("[stub email/whatsapp] would notify user=%s: %s — %s", user_id, title, body)
