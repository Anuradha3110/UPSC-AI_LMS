"""
notifications collection — MOD-10. The in-app channel is real and
DB-backed; email/WhatsApp Business API are logged, not sent (no SMTP or
WhatsApp Business account wired up in this build) — see
services/notify.py for exactly where a real sender plugs in.
"""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class NotificationType(str, Enum):
    revision_due = "revision_due"
    current_affairs_digest = "current_affairs_digest"
    mock_test_reminder = "mock_test_reminder"
    mentor_response = "mentor_response"
    evaluation_ready = "evaluation_ready"


class NotificationOut(BaseModel):
    id: str
    user_id: str
    type: NotificationType
    title: str
    body: str
    read: bool
    created_at: datetime
