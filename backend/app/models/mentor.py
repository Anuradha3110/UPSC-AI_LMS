"""
mentor_queue collection (§07) — the other half of MOD-07/MOD-09's human-
in-the-loop loop: a sample of scored Mains answers (Fig. 2's "~10%
sample / all Test-Series") routed to a mentor for override + rationale.
Mentor-override rate per rubric_version is the KPI §09/§13 both call out
by name.
"""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class MentorQueueStatus(str, Enum):
    pending = "pending"
    reviewed = "reviewed"


class MentorQueueItemOut(BaseModel):
    id: str
    submission_id: str
    evaluation_id: str
    assigned_mentor_id: str | None
    sla_due_at: datetime
    status: MentorQueueStatus
    # populated for the reviewer's convenience — not stored twice, joined at read time
    question_text: str
    answer_text: str
    ai_dimension_scores: dict
    ai_overall_score: float


class MentorOverrideRequest(BaseModel):
    override_score: float
    override_rationale: str
