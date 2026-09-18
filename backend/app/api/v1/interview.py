"""
MOD-08 — Personality Test Simulator. DAF profile is create-or-replace
(one per aspirant); a session is a running transcript the frontend polls
by re-fetching after each candidate turn.

Gated to the `full_prep` plan (README: "Prelims + Mains + Interview") via
`require_plan` — this is the access students unlock by clearing payment
for that tier.
"""
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_user, require_plan
from app.models.interview import DAFProfileCreate, DAFProfileOut, InterviewSessionOut
from app.services.interview import close_out_feedback, next_panel_turn

router = APIRouter(dependencies=[Depends(require_plan("full_prep"))])


@router.put("/daf", response_model=DAFProfileOut)
async def upsert_daf(
    payload: DAFProfileCreate,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = payload.model_dump()
    doc["user_id"] = str(user["_id"])
    await db.daf_profiles.update_one(
        {"user_id": doc["user_id"]}, {"$set": doc}, upsert=True
    )
    saved = await db.daf_profiles.find_one({"user_id": doc["user_id"]})
    return DAFProfileOut(id=str(saved["_id"]), **{k: saved[k] for k in DAFProfileCreate.model_fields}, user_id=doc["user_id"])


@router.get("/daf", response_model=DAFProfileOut | None)
async def get_daf(
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    saved = await db.daf_profiles.find_one({"user_id": str(user["_id"])})
    if not saved:
        return None
    return DAFProfileOut(id=str(saved["_id"]), **{k: saved[k] for k in DAFProfileCreate.model_fields}, user_id=saved["user_id"])


def _session_out(doc: dict) -> InterviewSessionOut:
    return InterviewSessionOut(
        id=str(doc["_id"]),
        user_id=doc["user_id"],
        status=doc["status"],
        transcript=doc["transcript"],
        feedback=doc.get("feedback"),
        created_at=doc["created_at"],
    )


@router.post("/sessions", response_model=InterviewSessionOut, status_code=201)
async def start_session(
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    daf = await db.daf_profiles.find_one({"user_id": str(user["_id"])})
    if not daf:
        raise HTTPException(400, "Fill in your DAF profile first (PUT /interview/daf)")

    opening_question = await next_panel_turn(daf, [])
    transcript = [{"role": "panel", "text": opening_question}]
    doc = {
        "user_id": str(user["_id"]),
        "status": "in_progress",
        "transcript": transcript,
        "feedback": None,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.interview_sessions.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _session_out(doc)


class CandidateReply(BaseModel):
    text: str


@router.post("/sessions/{session_id}/reply", response_model=InterviewSessionOut)
async def reply(
    session_id: str,
    payload: CandidateReply,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await db.interview_sessions.find_one({"_id": ObjectId(session_id)})
    if not doc or doc["user_id"] != str(user["_id"]):
        raise HTTPException(404, "Session not found")
    if doc["status"] != "in_progress":
        raise HTTPException(400, "Session already ended")

    daf = await db.daf_profiles.find_one({"user_id": str(user["_id"])})
    transcript = doc["transcript"] + [{"role": "candidate", "text": payload.text}]
    next_question = await next_panel_turn(daf, transcript)
    transcript.append({"role": "panel", "text": next_question})

    await db.interview_sessions.update_one({"_id": doc["_id"]}, {"$set": {"transcript": transcript}})
    doc["transcript"] = transcript
    return _session_out(doc)


@router.post("/sessions/{session_id}/end", response_model=InterviewSessionOut)
async def end_session(
    session_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await db.interview_sessions.find_one({"_id": ObjectId(session_id)})
    if not doc or doc["user_id"] != str(user["_id"]):
        raise HTTPException(404, "Session not found")

    daf = await db.daf_profiles.find_one({"user_id": str(user["_id"])})
    feedback = await close_out_feedback(daf, doc["transcript"])
    await db.interview_sessions.update_one(
        {"_id": doc["_id"]}, {"$set": {"status": "completed", "feedback": feedback}}
    )
    doc["status"] = "completed"
    doc["feedback"] = feedback
    return _session_out(doc)
