"""
MOD-04 — Prelims Test Engine (first working vertical slice per the
build-order: pure CRUD + scoring, no LLM). Enforces the real UPSC rule:
-1/3 mark per wrong answer, no penalty for an unattempted question.
"""
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.syllabus import Paper

router = APIRouter()

NEGATIVE_MARKING_FRACTION = 1 / 3


class MockTestOut(BaseModel):
    id: str
    paper: str
    question_ids: list[str]
    questions_preview: list[dict]  # question text + options, no answer key


class SubmitAttemptRequest(BaseModel):
    test_id: str
    # question_id -> chosen option label ("A"/"B"/"C"/"D"), omit if unattempted
    responses: dict[str, str]


class AttemptResult(BaseModel):
    raw_score: float
    correct: int
    wrong: int
    unattempted: int
    max_marks: float


@router.post("/prelims/mock", response_model=MockTestOut)
async def generate_mock_test(
    paper: Paper,
    question_count: int = 20,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    if paper not in (Paper.gs1, Paper.csat):
        raise HTTPException(400, "Prelims mock tests are GS1 or CSAT only")

    pipeline = [
        {"$match": {"paper": paper.value, "options": {"$exists": True}}},
        {"$sample": {"size": question_count}},
    ]
    questions = await db.pyq_bank.aggregate(pipeline).to_list(length=question_count)
    if not questions:
        raise HTTPException(404, f"No {paper.value} MCQs seeded yet — run app/seed.py")

    test_doc = {
        "paper": paper.value,
        "question_ids": [str(q["_id"]) for q in questions],
    }
    result = await db.mock_tests.insert_one(test_doc)

    preview = [
        {
            "id": str(q["_id"]),
            "question_text": q["question_text"],
            "marks": q["marks"],
            "options": q["options"],
        }
        for q in questions
    ]
    return MockTestOut(
        id=str(result.inserted_id),
        paper=paper.value,
        question_ids=test_doc["question_ids"],
        questions_preview=preview,
    )


@router.post("/prelims/submit", response_model=AttemptResult)
async def submit_attempt(
    payload: SubmitAttemptRequest,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    test = await db.mock_tests.find_one({"_id": ObjectId(payload.test_id)})
    if not test:
        raise HTTPException(404, "Test not found")

    questions = await db.pyq_bank.find(
        {"_id": {"$in": [ObjectId(qid) for qid in test["question_ids"]]}}
    ).to_list(length=len(test["question_ids"]))

    correct = wrong = unattempted = 0
    raw_score = 0.0
    max_marks = 0

    for q in questions:
        qid = str(q["_id"])
        max_marks += q["marks"]
        chosen = payload.responses.get(qid)
        if chosen is None:
            unattempted += 1
            continue
        if chosen == q["correct_option"]:
            correct += 1
            raw_score += q["marks"]
        else:
            wrong += 1
            raw_score -= q["marks"] * NEGATIVE_MARKING_FRACTION

    await db.test_attempts.insert_one(
        {
            "user_id": str(user["_id"]),
            "test_id": payload.test_id,
            "paper": test["paper"],
            "responses": payload.responses,
            "raw_score": raw_score,
            "correct": correct,
            "wrong": wrong,
            "unattempted": unattempted,
        }
    )

    return AttemptResult(
        raw_score=round(raw_score, 2),
        correct=correct,
        wrong=wrong,
        unattempted=unattempted,
        max_marks=max_marks,
    )
