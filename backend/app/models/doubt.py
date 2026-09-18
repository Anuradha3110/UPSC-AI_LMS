"""
doubts collection — MOD-07's conceptual-doubt half (the other half,
mentor QA sampling of graded Mains answers, lives in mentor_queue via
models/mentor.py). Not in §07's table verbatim, but implied by MOD-07's
module card: "conceptual doubts get an AI first-pass answer; anything
low-confidence or explicitly flagged escalates to a human mentor."
"""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class DoubtStatus(str, Enum):
    ai_answered = "ai_answered"
    escalated = "escalated"
    resolved = "resolved"


class DoubtCreate(BaseModel):
    question_text: str
    syllabus_node_id: str | None = None


class Citation(BaseModel):
    content_item_id: str
    title: str
    excerpt: str


class DoubtOut(BaseModel):
    id: str
    user_id: str
    question_text: str
    syllabus_node_id: str | None
    ai_answer: str | None
    citations: list[Citation] = Field(default_factory=list)
    confidence: str | None = None  # "high" | "low" — low auto-escalates
    status: DoubtStatus
    mentor_response: str | None = None
    assigned_mentor_id: str | None = None
    created_at: datetime
