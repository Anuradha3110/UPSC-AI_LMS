"""
MOD-03's study/annotation layer: bookmarks, text highlights (+ optional
note), and per-article reading progress — all private per authenticated
user (every query is scoped by user_id from the JWT, same pattern as
revision.py/notifications.py). Read routes that list saved items also
return a `content` summary so the "My Study Material" page doesn't have
to make N follow-up requests to resolve titles.
"""
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.study import (
    AnnotationCreate,
    AnnotationOut,
    AnnotationUpdate,
    BookmarkOut,
    ProgressOut,
    ProgressUpdate,
)

router = APIRouter()


async def _content_summaries(db: AsyncIOMotorDatabase, content_ids: list[str]) -> dict[str, dict]:
    object_ids = []
    for cid in set(content_ids):
        try:
            object_ids.append(ObjectId(cid))
        except Exception:
            continue
    docs = await db.content_items.find({"_id": {"$in": object_ids}}).to_list(length=len(object_ids))
    return {
        str(d["_id"]): {
            "id": str(d["_id"]),
            "title": d["title"],
            "category": d.get("category"),
            "source_name": d.get("source_name"),
            "published_at": d.get("published_at"),
        }
        for d in docs
    }


# ---------------------------------------------------------------- bookmarks

@router.get("/bookmarks")
async def list_bookmarks(
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    docs = (
        await db.bookmarks.find({"user_id": str(user["_id"])})
        .sort("created_at", -1)
        .to_list(length=500)
    )
    summaries = await _content_summaries(db, [d["content_item_id"] for d in docs])
    return [
        {
            "id": str(d["_id"]),
            "user_id": d["user_id"],
            "content_item_id": d["content_item_id"],
            "created_at": d["created_at"],
            "content": summaries.get(d["content_item_id"]),
        }
        for d in docs
    ]


@router.post("/bookmarks", response_model=BookmarkOut, status_code=201)
async def add_bookmark(
    content_item_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    existing = await db.bookmarks.find_one(
        {"user_id": str(user["_id"]), "content_item_id": content_item_id}
    )
    if existing:
        return BookmarkOut(
            id=str(existing["_id"]),
            user_id=existing["user_id"],
            content_item_id=existing["content_item_id"],
            created_at=existing["created_at"],
        )
    doc = {
        "user_id": str(user["_id"]),
        "content_item_id": content_item_id,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.bookmarks.insert_one(doc)
    return BookmarkOut(id=str(result.inserted_id), **doc)


@router.delete("/bookmarks/{content_item_id}", status_code=204)
async def remove_bookmark(
    content_item_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    await db.bookmarks.delete_one(
        {"user_id": str(user["_id"]), "content_item_id": content_item_id}
    )


# -------------------------------------------------------------- annotations

@router.get("/annotations")
async def list_annotations(
    content_item_id: str | None = None,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    query: dict = {"user_id": str(user["_id"])}
    if content_item_id:
        query["content_item_id"] = content_item_id
    docs = (
        await db.annotations.find(query).sort("created_at", -1).to_list(length=1000)
    )
    if content_item_id:
        return [_annotation_out(d) for d in docs]
    summaries = await _content_summaries(db, [d["content_item_id"] for d in docs])
    return [
        {**_annotation_out(d).model_dump(), "content": summaries.get(d["content_item_id"])}
        for d in docs
    ]


def _annotation_out(d: dict) -> AnnotationOut:
    return AnnotationOut(
        id=str(d["_id"]),
        user_id=d["user_id"],
        content_item_id=d["content_item_id"],
        color=d["color"],
        selected_text=d["selected_text"],
        start_offset=d["start_offset"],
        end_offset=d["end_offset"],
        note_text=d.get("note_text"),
        created_at=d["created_at"],
        updated_at=d["updated_at"],
    )


@router.post("/annotations", response_model=AnnotationOut, status_code=201)
async def create_annotation(
    payload: AnnotationCreate,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    doc = {
        "user_id": str(user["_id"]),
        "content_item_id": payload.content_item_id,
        "color": payload.color.value,
        "selected_text": payload.selected_text,
        "start_offset": payload.start_offset,
        "end_offset": payload.end_offset,
        "note_text": payload.note_text,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.annotations.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _annotation_out(doc)


@router.patch("/annotations/{annotation_id}", response_model=AnnotationOut)
async def update_annotation(
    annotation_id: str,
    payload: AnnotationUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    existing = await db.annotations.find_one(
        {"_id": ObjectId(annotation_id), "user_id": str(user["_id"])}
    )
    if not existing:
        raise HTTPException(404, "Annotation not found")

    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if "color" in updates:
        updates["color"] = payload.color.value
    updates["updated_at"] = datetime.now(timezone.utc)
    await db.annotations.update_one({"_id": existing["_id"]}, {"$set": updates})

    doc = await db.annotations.find_one({"_id": existing["_id"]})
    return _annotation_out(doc)


@router.delete("/annotations/{annotation_id}", status_code=204)
async def delete_annotation(
    annotation_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    await db.annotations.delete_one(
        {"_id": ObjectId(annotation_id), "user_id": str(user["_id"])}
    )


# ----------------------------------------------------------------- progress

@router.put("/progress/{content_item_id}", response_model=ProgressOut)
async def upsert_progress(
    content_item_id: str,
    payload: ProgressUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    await db.reading_progress.update_one(
        {"user_id": str(user["_id"]), "content_item_id": content_item_id},
        {"$set": {"progress_percent": payload.progress_percent, "updated_at": now}},
        upsert=True,
    )
    return ProgressOut(
        content_item_id=content_item_id, progress_percent=payload.progress_percent, updated_at=now
    )


@router.get("/progress/continue")
async def continue_reading(
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """The most recent article the aspirant was reading but hasn't
    finished — null if there isn't one."""
    doc = await db.reading_progress.find_one(
        {
            "user_id": str(user["_id"]),
            "progress_percent": {"$gt": 3, "$lt": 95},
        },
        sort=[("updated_at", -1)],
    )
    if not doc:
        return None
    summaries = await _content_summaries(db, [doc["content_item_id"]])
    return {
        "content_item_id": doc["content_item_id"],
        "progress_percent": doc["progress_percent"],
        "updated_at": doc["updated_at"],
        "content": summaries.get(doc["content_item_id"]),
    }
