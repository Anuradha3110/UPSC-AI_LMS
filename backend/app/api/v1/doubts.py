"""
MOD-07 — conceptual doubt-resolution half. Low-confidence or
zero-grounding answers auto-escalate to a mentor (`status="escalated"`);
mentors resolve them from api/v1/mentor.py's queue endpoints.
"""
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.doubt import DoubtCreate, DoubtOut
from app.services.doubts import resolve_doubt

router = APIRouter()


def _to_out(doc: dict) -> DoubtOut:
    return DoubtOut(
        id=str(doc["_id"]),
        user_id=doc["user_id"],
        question_text=doc["question_text"],
        syllabus_node_id=doc.get("syllabus_node_id"),
        ai_answer=doc.get("ai_answer"),
        citations=doc.get("citations", []),
        confidence=doc.get("confidence"),
        status=doc["status"],
        mentor_response=doc.get("mentor_response"),
        assigned_mentor_id=doc.get("assigned_mentor_id"),
        created_at=doc["created_at"],
    )


@router.get("", response_model=list[DoubtOut])
async def list_my_doubts(
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    docs = await db.doubts.find({"user_id": str(user["_id"])}).sort("created_at", -1).to_list(length=100)
    return [_to_out(d) for d in docs]


@router.post("", response_model=DoubtOut, status_code=201)
async def ask_doubt(
    payload: DoubtCreate,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    result = await resolve_doubt(db, payload.question_text, payload.syllabus_node_id)
    status_ = "escalated" if result["confidence"] != "high" else "ai_answered"

    doc = {
        "user_id": str(user["_id"]),
        "question_text": payload.question_text,
        "syllabus_node_id": payload.syllabus_node_id,
        "ai_answer": result["ai_answer"],
        "citations": result["citations"],
        "confidence": result["confidence"],
        "status": status_,
        "mentor_response": None,
        "assigned_mentor_id": None,
        "created_at": datetime.now(timezone.utc),
    }
    insert_result = await db.doubts.insert_one(doc)
    doc["_id"] = insert_result.inserted_id
    return _to_out(doc)


@router.post("/{doubt_id}/escalate", response_model=DoubtOut)
async def escalate_doubt(
    doubt_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """An aspirant can explicitly flag the AI's answer as unsatisfactory."""
    doc = await db.doubts.find_one({"_id": ObjectId(doubt_id)})
    if not doc or doc["user_id"] != str(user["_id"]):
        raise HTTPException(404, "Doubt not found")
    await db.doubts.update_one({"_id": doc["_id"]}, {"$set": {"status": "escalated"}})
    doc["status"] = "escalated"
    return _to_out(doc)
