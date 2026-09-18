"""
MOD-07/09 — mentor-facing side: the QA queue sampled from graded Mains
answers (Fig. 2), the override console, and escalated doubts. Every
endpoint here is mentor/admin-only. Override rate per rubric_version —
the KPI §09/§13 call out by name — is computed in api/v1/analytics.py
from the same mentor_queue collection this router writes to.
"""
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.deps import require_role
from app.models.doubt import DoubtOut
from app.models.mentor import MentorOverrideRequest, MentorQueueItemOut

router = APIRouter()


@router.get("/queue", response_model=list[MentorQueueItemOut])
async def list_queue(
    status_filter: str = "pending",
    _user: dict = Depends(require_role("mentor", "admin")),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    items = await db.mentor_queue.find({"status": status_filter}).to_list(length=100)
    out = []
    for item in items:
        submission = await db.answer_submissions.find_one({"_id": ObjectId(item["submission_id"])})
        evaluation = await db.answer_evaluations.find_one({"_id": ObjectId(item["evaluation_id"])})
        if not submission or not evaluation:
            continue
        pyq = await db.pyq_bank.find_one({"_id": ObjectId(submission["pyq_id"])})
        out.append(
            MentorQueueItemOut(
                id=str(item["_id"]),
                submission_id=item["submission_id"],
                evaluation_id=item["evaluation_id"],
                assigned_mentor_id=item.get("assigned_mentor_id"),
                sla_due_at=item["sla_due_at"],
                status=item["status"],
                question_text=pyq["question_text"] if pyq else "(question deleted)",
                answer_text=submission["answer_text"],
                ai_dimension_scores=evaluation["dimension_scores"],
                ai_overall_score=evaluation["overall_score"],
            )
        )
    return out


@router.post("/queue/{item_id}/override")
async def override_evaluation(
    item_id: str,
    payload: MentorOverrideRequest,
    user: dict = Depends(require_role("mentor", "admin")),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    item = await db.mentor_queue.find_one({"_id": ObjectId(item_id)})
    if not item:
        raise HTTPException(404, "Queue item not found")

    await db.answer_evaluations.update_one(
        {"_id": ObjectId(item["evaluation_id"])},
        {
            "$set": {
                "mentor_override": {
                    "mentor_id": str(user["_id"]),
                    "override_score": payload.override_score,
                    "override_rationale": payload.override_rationale,
                    "overridden_at": datetime.now(timezone.utc),
                }
            }
        },
    )
    await db.mentor_queue.update_one(
        {"_id": item["_id"]},
        {"$set": {"status": "reviewed", "assigned_mentor_id": str(user["_id"])}},
    )
    return {"status": "reviewed"}


@router.get("/doubts", response_model=list[DoubtOut])
async def list_escalated_doubts(
    _user: dict = Depends(require_role("mentor", "admin")),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    docs = await db.doubts.find({"status": "escalated"}).sort("created_at", 1).to_list(length=100)
    return [
        DoubtOut(
            id=str(d["_id"]),
            user_id=d["user_id"],
            question_text=d["question_text"],
            syllabus_node_id=d.get("syllabus_node_id"),
            ai_answer=d.get("ai_answer"),
            citations=d.get("citations", []),
            confidence=d.get("confidence"),
            status=d["status"],
            mentor_response=d.get("mentor_response"),
            assigned_mentor_id=d.get("assigned_mentor_id"),
            created_at=d["created_at"],
        )
        for d in docs
    ]


@router.post("/doubts/{doubt_id}/respond", response_model=DoubtOut)
async def respond_to_doubt(
    doubt_id: str,
    response_text: str,
    user: dict = Depends(require_role("mentor", "admin")),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await db.doubts.find_one({"_id": ObjectId(doubt_id)})
    if not doc:
        raise HTTPException(404, "Doubt not found")

    from app.models.notification import NotificationType
    from app.services.notify import notify

    await db.doubts.update_one(
        {"_id": doc["_id"]},
        {
            "$set": {
                "status": "resolved",
                "mentor_response": response_text,
                "assigned_mentor_id": str(user["_id"]),
            }
        },
    )
    await notify(
        db,
        doc["user_id"],
        NotificationType.mentor_response,
        "A mentor answered your doubt",
        response_text[:200],
    )
    doc.update(status="resolved", mentor_response=response_text, assigned_mentor_id=str(user["_id"]))
    return DoubtOut(
        id=str(doc["_id"]),
        user_id=doc["user_id"],
        question_text=doc["question_text"],
        syllabus_node_id=doc.get("syllabus_node_id"),
        ai_answer=doc.get("ai_answer"),
        citations=doc.get("citations", []),
        confidence=doc.get("confidence"),
        status=doc["status"],
        mentor_response=doc["mentor_response"],
        assigned_mentor_id=doc["assigned_mentor_id"],
        created_at=doc["created_at"],
    )
