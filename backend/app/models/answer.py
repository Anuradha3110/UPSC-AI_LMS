"""
answer_submissions + answer_evaluations (§07). The four dimension_scores
keys match §05's MOD-05 card exactly — content coverage, structure,
word-limit discipline, value-addition — the same axes a real UPSC
examiner marks against.
"""
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class AnswerSubmissionCreate(BaseModel):
    pyq_id: str
    answer_text: str


class DimensionScores(BaseModel):
    content_coverage: int = Field(ge=0, le=10)
    structure: int = Field(ge=0, le=10)
    word_limit_adherence: int = Field(ge=0, le=10)
    value_addition: int = Field(ge=0, le=10)


class AnswerEvaluationOut(BaseModel):
    id: str
    submission_id: str
    rubric_version: str
    dimension_scores: DimensionScores
    overall_score: float
    max_marks: float
    feedback_text: str
    word_count: int
    expected_word_limit: int
    created_at: datetime


class AnswerSubmissionOut(BaseModel):
    id: str
    pyq_id: str
    answer_text: str
    submission_type: str = "typed"  # "typed" | "scanned"
    status: str  # "queued" | "grading" | "graded" | "grading_failed"
    submitted_at: datetime
    evaluation: AnswerEvaluationOut | None = None


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
