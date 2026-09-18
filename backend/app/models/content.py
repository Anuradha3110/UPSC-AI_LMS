"""
content_items collection (§07) — MOD-02's reading material and MOD-03's
current-affairs digest share one collection, distinguished by
`source_type`. Real Atlas Vector Search embeddings are a later swap;
for now `syllabus_node_ids` is populated by a one-shot Claude
classification call at ingest time (see services/tagging.py) instead of
embedding similarity — same AI touchpoint the architecture describes,
simpler retrieval path until the PYQ/content volume justifies a vector
index.
"""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.models.pyq import MCQOption


class SourceType(str, Enum):
    ncert = "ncert"                    # public domain, safe to store verbatim
    pib = "pib"
    prs_bill_tracker = "prs_bill_tracker"
    editorial = "editorial"
    economic_survey = "economic_survey"
    derived_summary = "derived_summary"  # platform-authored summary of a licensed reference


class CurrentAffairsCategory(str, Enum):
    """MOD-03's UPSC-relevance categories — set by services/news_ingest.py's
    classification step; content that isn't current-affairs (syllabus
    reading material) leaves this null."""
    polity_governance = "polity_governance"
    economy = "economy"
    international_relations = "international_relations"
    environment = "environment"
    science_tech = "science_tech"
    history_culture = "history_culture"
    geography = "geography"
    social_issues = "social_issues"
    government_schemes = "government_schemes"
    defence = "defence"
    reports_indices = "reports_indices"
    awards_appointments = "awards_appointments"
    other = "other"


class CurrentAffairsMCQ(BaseModel):
    question_text: str
    options: list[MCQOption]
    correct_option: str
    explanation: str


class ContentItemCreate(BaseModel):
    title: str
    body: str
    source_type: SourceType
    source_url: str | None = None
    source_name: str | None = None
    syllabus_node_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    is_current_affairs: bool = False
    published_at: datetime | None = None

    # MOD-03's AI-processing "exam pack" — populated by services/news_ingest.py
    # for ingested current-affairs items; null for syllabus reading material
    # and for anything created before this was added (old rows just render
    # without these sections, nothing breaks).
    category: CurrentAffairsCategory | None = None
    prelims_facts: list[str] = Field(default_factory=list)
    mains_perspective: str | None = None
    possible_questions: list[str] = Field(default_factory=list)
    mcq: CurrentAffairsMCQ | None = None


class ContentItemOut(ContentItemCreate):
    id: str
