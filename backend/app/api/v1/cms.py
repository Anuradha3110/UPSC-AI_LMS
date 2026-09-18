"""
MOD-11 — Content & Marketing CMS, the question-bank/rubric half (the
public lead-gen site is a frontend-only concern — see frontend/app/(marketing)).
content_editor/admin write PYQs and marking schemes through here;
api/v1/content.py covers the equivalent for reading material and
current-affairs items.
"""
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.core.database import get_db
from app.core.deps import require_role
from app.models.pyq import PYQCreate, PYQOut

router = APIRouter()


def _to_out(doc: dict) -> PYQOut:
    return PYQOut(
        id=str(doc["_id"]),
        year=doc["year"],
        paper=doc["paper"],
        question_text=doc["question_text"],
        marks=doc["marks"],
        syllabus_node_ids=doc.get("syllabus_node_ids", []),
        optional_subject=doc.get("optional_subject"),
        options=doc.get("options"),
        correct_option=doc.get("correct_option"),
        marking_scheme=doc.get("marking_scheme"),
    )


@router.get("/pyqs", response_model=list[PYQOut])
async def list_pyqs(
    _user: dict = Depends(require_role("content_editor", "admin")),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    docs = await db.pyq_bank.find({}).to_list(length=2000)
    return [_to_out(d) for d in docs]


@router.post("/pyqs", response_model=PYQOut, status_code=201)
async def create_pyq(
    payload: PYQCreate,
    _user: dict = Depends(require_role("content_editor", "admin")),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = payload.model_dump()
    result = await db.pyq_bank.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_out(doc)


@router.put("/pyqs/{pyq_id}", response_model=PYQOut)
async def update_pyq(
    pyq_id: str,
    payload: PYQCreate,
    _user: dict = Depends(require_role("content_editor", "admin")),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    result = await db.pyq_bank.find_one_and_update(
        {"_id": ObjectId(pyq_id)}, {"$set": payload.model_dump()}, return_document=ReturnDocument.AFTER
    )
    if not result:
        raise HTTPException(404, "PYQ not found")
    return _to_out(result)


@router.delete("/pyqs/{pyq_id}", status_code=204)
async def delete_pyq(
    pyq_id: str,
    _user: dict = Depends(require_role("content_editor", "admin")),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    await db.pyq_bank.delete_one({"_id": ObjectId(pyq_id)})
