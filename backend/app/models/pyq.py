"""
pyq_bank collection (§07). MCQs power MOD-04 (Prelims Test Engine);
descriptive entries are what MOD-05's rubric retrieval pulls a marking
scheme from.
"""
from pydantic import BaseModel, Field

from app.models.syllabus import Paper


class MCQOption(BaseModel):
    label: str  # "A" | "B" | "C" | "D"
    text: str


class PYQCreate(BaseModel):
    year: int
    paper: Paper
    question_text: str
    marks: float  # CSAT MCQs can carry fractional marks (e.g. 2.5)
    syllabus_node_ids: list[str] = Field(default_factory=list)
    # only set when paper == OPTIONAL, e.g. "Public Administration" — matches
    # UserCreate.optional_subject / SyllabusNodeCreate.optional_subject
    optional_subject: str | None = None

    # Prelims-only fields
    options: list[MCQOption] | None = None
    correct_option: str | None = None

    # Mains-only field
    marking_scheme: str | None = None


class PYQOut(PYQCreate):
    id: str
