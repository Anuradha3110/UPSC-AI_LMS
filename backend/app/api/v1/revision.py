"""
MOD-06 — Revision & Spaced-Repetition Scheduler. `GET /due` is the
aspirant's revision queue; `POST /{node_id}/review` records a self-rated
recall and advances that node's SM-2 state, nudged by the aspirant's
most recent graded performance on the same node when one exists.
"""
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.revision import ReviewQuality, RevisionItemOut
from app.services.revision import adjust_from_signal, next_due_at, sm2_update

router = APIRouter()


async def _recent_score_ratio(db: AsyncIOMotorDatabase, user_id: str, node_id: str) -> float | None:
    pyq_ids = [
        str(p["_id"])
        for p in await db.pyq_bank.find({"syllabus_node_ids": node_id}, {"_id": 1}).to_list(length=200)
    ]
    if not pyq_ids:
        return None
    submission = await db.answer_submissions.find_one(
        {"user_id": user_id, "pyq_id": {"$in": pyq_ids}, "status": "graded"},
        sort=[("submitted_at", -1)],
    )
    if not submission:
        return None
    evaluation = await db.answer_evaluations.find_one({"submission_id": str(submission["_id"])})
    if not evaluation or not evaluation.get("max_marks"):
        return None
    return evaluation["overall_score"] / evaluation["max_marks"]


@router.get("/due", response_model=list[RevisionItemOut])
async def list_due(
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    docs = await db.revision_schedule.find(
        {"user_id": str(user["_id"]), "next_due_at": {"$lte": now}}
    ).to_list(length=200)

    out = []
    for d in docs:
        node = await db.syllabus_nodes.find_one({"_id": ObjectId(d["syllabus_node_id"])})
        out.append(
            RevisionItemOut(
                id=str(d["_id"]),
                user_id=d["user_id"],
                syllabus_node_id=d["syllabus_node_id"],
                syllabus_node_title=node["title"] if node else "(deleted node)",
                next_due_at=d["next_due_at"],
                interval=d["interval"],
                ease_factor=d["ease_factor"],
                repetitions=d["repetitions"],
            )
        )
    return out


@router.post("/{node_id}/review", response_model=RevisionItemOut)
async def review_node(
    node_id: str,
    payload: ReviewQuality,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    node = await db.syllabus_nodes.find_one({"_id": ObjectId(node_id)})
    if not node:
        raise HTTPException(404, "Syllabus node not found")

    state = await db.revision_schedule.find_one(
        {"user_id": str(user["_id"]), "syllabus_node_id": node_id}
    )
    interval = state["interval"] if state else 0
    ease_factor = state["ease_factor"] if state else 2.5
    repetitions = state["repetitions"] if state else 0

    ratio = await _recent_score_ratio(db, str(user["_id"]), node_id)
    quality = adjust_from_signal(payload.quality, ratio)

    new_interval, new_ease, new_reps = sm2_update(interval, ease_factor, repetitions, quality)
    update = {
        "user_id": str(user["_id"]),
        "syllabus_node_id": node_id,
        "next_due_at": next_due_at(new_interval),
        "interval": new_interval,
        "ease_factor": new_ease,
        "repetitions": new_reps,
    }

    if state:
        await db.revision_schedule.update_one({"_id": state["_id"]}, {"$set": update})
        doc_id = state["_id"]
    else:
        result = await db.revision_schedule.insert_one(update)
        doc_id = result.inserted_id

    return RevisionItemOut(id=str(doc_id), syllabus_node_title=node["title"], **update)
