"""
MOD-02 (reading material per syllabus node) + MOD-03 (current-affairs
digest). Both read content_items; content_editor/admin can write
through here too (kept alongside cms.py's PYQ/rubric writes rather than
duplicated there) since content_items is this router's collection.
"""
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.deps import require_role
from app.models.content import ContentItemCreate, ContentItemOut, CurrentAffairsCategory
from app.services.news_ingest import ingest_current_affairs
from app.services.tagging import tag_to_syllabus_nodes

router = APIRouter()


def _to_out(doc: dict) -> ContentItemOut:
    return ContentItemOut(
        id=str(doc["_id"]),
        title=doc["title"],
        body=doc["body"],
        source_type=doc["source_type"],
        source_url=doc.get("source_url"),
        source_name=doc.get("source_name"),
        syllabus_node_ids=doc.get("syllabus_node_ids", []),
        tags=doc.get("tags", []),
        is_current_affairs=doc.get("is_current_affairs", False),
        published_at=doc.get("published_at"),
        category=doc.get("category"),
        prelims_facts=doc.get("prelims_facts", []),
        mains_perspective=doc.get("mains_perspective"),
        possible_questions=doc.get("possible_questions", []),
        mcq=doc.get("mcq"),
    )


@router.get("", response_model=list[ContentItemOut])
async def list_content(
    syllabus_node_id: str | None = None,
    is_current_affairs: bool | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    query: dict = {}
    if syllabus_node_id:
        query["syllabus_node_ids"] = syllabus_node_id
    if is_current_affairs is not None:
        query["is_current_affairs"] = is_current_affairs
    docs = await db.content_items.find(query).sort("published_at", -1).to_list(length=200)
    return [_to_out(d) for d in docs]


@router.get("/digest", response_model=list[ContentItemOut])
async def current_affairs_digest(
    days: int = Query(default=90, ge=1, le=365),
    category: CurrentAffairsCategory | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """MOD-03: one compiled digest, computed once and shared across every
    aspirant who reads it — not regenerated per request (§10 NFR). Returns
    enough of a window (150 items) for the frontend to group client-side
    into Today / Previous days / Monthly without a separate endpoint per view."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    query: dict = {"is_current_affairs": True, "published_at": {"$gte": cutoff}}
    if category:
        query["category"] = category.value
    docs = (
        await db.content_items.find(query)
        .sort("published_at", -1)
        .limit(150)
        .to_list(length=150)
    )
    return [_to_out(d) for d in docs]


@router.get("/{content_id}", response_model=ContentItemOut)
async def get_content_item(
    content_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await db.content_items.find_one({"_id": ObjectId(content_id)})
    if not doc:
        raise HTTPException(404, "Content item not found")
    return _to_out(doc)


@router.post("/current-affairs/refresh")
async def refresh_current_affairs(
    _user: dict = Depends(require_role("content_editor", "admin")),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Runs the daily ingest on demand — normally main.py's startup loop
    does this automatically every 24h, this is just for testing/forcing
    a refresh without waiting."""
    count = await ingest_current_affairs(db)
    return {"inserted": count}


@router.post("", response_model=ContentItemOut, status_code=201)
async def create_content(
    payload: ContentItemCreate,
    _user: dict = Depends(require_role("content_editor", "admin")),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = payload.model_dump()
    if not doc["syllabus_node_ids"]:
        doc["syllabus_node_ids"] = await tag_to_syllabus_nodes(db, payload.title, payload.body)
    if doc.get("published_at") is None:
        doc["published_at"] = datetime.now(timezone.utc)
    result = await db.content_items.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_out(doc)


@router.delete("/{content_id}", status_code=204)
async def delete_content(
    content_id: str,
    _user: dict = Depends(require_role("content_editor", "admin")),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    await db.content_items.delete_one({"_id": ObjectId(content_id)})
