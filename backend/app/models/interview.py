"""
daf_profiles + interview_sessions (§07) — MOD-08. Text-based panel
simulator for this build (§14 build-scope note: voice articulation is a
Phase-4 extension, out of scope here). DAF data is sensitive PII per
§09 — scoped to this module only, never joined into general analytics.
"""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class DAFProfileCreate(BaseModel):
    cadre_preference: list[str] = Field(default_factory=list)
    optional_subject: str
    hobbies: list[str] = Field(default_factory=list)
    work_experience: str | None = None
    home_district: str
    home_state: str
    graduation_field: str | None = None
    extra_notes: str | None = None


class DAFProfileOut(DAFProfileCreate):
    id: str
    user_id: str


class InterviewTurn(BaseModel):
    role: str  # "panel" | "candidate"
    text: str


class InterviewSessionStatus(str, Enum):
    in_progress = "in_progress"
    completed = "completed"


class InterviewSessionOut(BaseModel):
    id: str
    user_id: str
    status: InterviewSessionStatus
    transcript: list[InterviewTurn]
    feedback: str | None = None
    created_at: datetime
