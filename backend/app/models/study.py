"""
Study & annotation feature for MOD-03's current-affairs reading experience:
bookmarks, text highlights (optionally carrying a note), and per-article
reading progress. Three focused collections rather than one — each has a
different access pattern (bookmarks toggle, annotations list-by-article,
progress is a single upsert-per-article row) and this matches the rest of
the app's one-collection-per-concern style (revision_schedule, notifications, ...).
"""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class HighlightColor(str, Enum):
    yellow = "yellow"   # Important
    green = "green"     # Key Fact
    blue = "blue"       # Concept
    pink = "pink"       # Revision


class BookmarkOut(BaseModel):
    id: str
    user_id: str
    content_item_id: str
    created_at: datetime


class AnnotationCreate(BaseModel):
    content_item_id: str
    color: HighlightColor
    selected_text: str
    start_offset: int
    end_offset: int
    note_text: str | None = None


class AnnotationUpdate(BaseModel):
    color: HighlightColor | None = None
    note_text: str | None = None


class AnnotationOut(BaseModel):
    id: str
    user_id: str
    content_item_id: str
    color: HighlightColor
    selected_text: str
    start_offset: int
    end_offset: int
    note_text: str | None = None
    created_at: datetime
    updated_at: datetime


class ProgressUpdate(BaseModel):
    progress_percent: float = Field(ge=0, le=100)


class ProgressOut(BaseModel):
    content_item_id: str
    progress_percent: float
    updated_at: datetime
