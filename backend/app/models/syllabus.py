"""
syllabus_nodes collection (§07) — the graph every other module (tests,
current affairs, revision, PYQs) tags itself against. Get this model
right before seeding content; changing `paper` values later means
re-tagging everything downstream.
"""
from enum import Enum

from pydantic import BaseModel, Field


class Paper(str, Enum):
    gs1 = "GS1"
    gs2 = "GS2"
    gs3 = "GS3"
    gs4 = "GS4"
    csat = "CSAT"
    essay = "ESSAY"
    optional = "OPTIONAL"


class SyllabusNodeCreate(BaseModel):
    paper: Paper
    title: str
    parent_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    # only set when paper == OPTIONAL, e.g. "Public Administration"
    optional_subject: str | None = None


class SyllabusNodeOut(SyllabusNodeCreate):
    id: str
