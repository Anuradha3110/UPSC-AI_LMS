"""
MOD-06 — Revision & Spaced-Repetition Scheduler. Standard SM-2 update,
with one deviation from the textbook algorithm per §05's module card:
`adjust_from_signal` nudges the quality rating using real graded-answer/
mock-test performance on the same syllabus node, instead of leaving the
interval purely to a self-rated "I remember this."
"""
from datetime import datetime, timedelta, timezone

MIN_EASE_FACTOR = 1.3


def sm2_update(interval: int, ease_factor: float, repetitions: int, quality: int) -> tuple[int, float, int]:
    """Returns (new_interval_days, new_ease_factor, new_repetitions)."""
    quality = max(0, min(5, quality))

    if quality < 3:
        # Failed recall — restart the interval ladder, keep the ease factor.
        return 1, ease_factor, 0

    if repetitions == 0:
        new_interval = 1
    elif repetitions == 1:
        new_interval = 6
    else:
        new_interval = round(interval * ease_factor)

    new_ease = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_ease = max(MIN_EASE_FACTOR, new_ease)

    return new_interval, new_ease, repetitions + 1


def adjust_from_signal(quality: int, recent_score_ratio: float | None) -> int:
    """
    recent_score_ratio: the aspirant's most recent graded-answer or mock
    score on this node as a 0-1 fraction of max marks, if one exists.
    Nudges the self-rated quality up/down by at most 1 point so real
    performance can't be entirely talked over by a generous self-rating.
    """
    if recent_score_ratio is None:
        return quality
    if recent_score_ratio >= 0.75 and quality < 5:
        return quality + 1
    if recent_score_ratio < 0.4 and quality > 0:
        return quality - 1
    return quality


def next_due_at(interval_days: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=interval_days)
