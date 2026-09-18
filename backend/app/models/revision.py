"""
revision_schedule collection (§07) — MOD-06. SM-2-style spaced
repetition per syllabus node, per user. `ease_factor`/`interval`/
`repetitions` are the standard SM-2 state triple; §05's module card
calls for intervals that also react to real graded-answer/mock-test
signal, not just a self-rating — `adjust_from_signal` in
services/revision.py is where that hook lives.
"""
from datetime import datetime

from pydantic import BaseModel


class ReviewQuality(BaseModel):
    # 0-5, SM-2's own self-rated recall scale: 0 = total blackout, 5 = perfect recall
    quality: int


class RevisionItemOut(BaseModel):
    id: str
    user_id: str
    syllabus_node_id: str
    syllabus_node_title: str
    next_due_at: datetime
    interval: int
    ease_factor: float
    repetitions: int
