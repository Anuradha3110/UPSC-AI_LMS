"""
MOD-05 — Mains Answer-Writing & Evaluation Engine.

Grading now runs as a background task instead of inline on the request
(§08/§10's "queued, never run inline" requirement) — the prototype
substitute for a Redis-backed worker pool: `submit_answer` returns
`status: "queued"` immediately and `_run_grading` updates the document
once Claude responds, so the frontend polls GET /{id} the same way it
would against a real queue. Swapping in Redis + RQ/Celery later means
replacing `background_tasks.add_task(...)` with an enqueue call — the
grading function itself doesn't change.

Also covers: OCR intake for photographed answers (Fig. 2's second input
path), the mentor QA sample (Fig. 2's "~10% sample" arrow into
mentor_queue), the evaluation-ready notification, and per-plan AI-usage
quota enforcement (§09's "AI usage quotas enforced at the orchestration
layer, not reconciled after the bill arrives").
"""
import random
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import db as _db, get_db
from app.core.deps import get_current_user
from app.models.answer import AnswerEvaluationOut, AnswerSubmissionCreate, AnswerSubmissionOut
from app.models.notification import NotificationType
from app.services.billing import check_and_consume_ai_quota
from app.services.grading import grade_answer
from app.services.notify import notify
from app.services.ocr import transcribe_handwritten_answer

router = APIRouter()

MENTOR_SAMPLE_RATE = 0.10  # Fig. 2: "~10% sample / all Test-Series"


@router.get("/questions")
async def list_practice_questions(
    paper: str | None = None,
    optional_subject: str | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Descriptive (non-MCQ) PYQs — what the answer-writing workspace lets you pick from."""
    query: dict = {"options": None}
    if paper:
        query["paper"] = paper
    if optional_subject:
        query["optional_subject"] = optional_subject
    docs = await db.pyq_bank.find(query).to_list(length=200)
    return [
        {
            "id": str(d["_id"]),
            "paper": d["paper"],
            "marks": d["marks"],
            "question_text": d["question_text"],
            "optional_subject": d.get("optional_subject"),
        }
        for d in docs
    ]


@router.get("", response_model=list[AnswerSubmissionOut])
async def list_my_submissions(
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    docs = await db.answer_submissions.find({"user_id": str(user["_id"])}).sort("submitted_at", -1).to_list(length=100)
    out = []
    for doc in docs:
        evaluation = await db.answer_evaluations.find_one({"submission_id": str(doc["_id"])})
        out.append(_submission_out(doc, evaluation))
    return out


def _evaluation_out(doc: dict) -> AnswerEvaluationOut:
    return AnswerEvaluationOut(
        id=str(doc["_id"]),
        submission_id=doc["submission_id"],
        rubric_version=doc["rubric_version"],
        dimension_scores=doc["dimension_scores"],
        overall_score=doc["overall_score"],
        max_marks=doc["max_marks"],
        feedback_text=doc["feedback_text"],
        word_count=doc["word_count"],
        expected_word_limit=doc["expected_word_limit"],
        created_at=doc["created_at"],
    )


def _submission_out(doc: dict, evaluation: dict | None) -> AnswerSubmissionOut:
    return AnswerSubmissionOut(
        id=str(doc["_id"]),
        pyq_id=doc["pyq_id"],
        answer_text=doc["answer_text"],
        submission_type=doc.get("submission_type", "typed"),
        status=doc["status"],
        submitted_at=doc["submitted_at"],
        evaluation=_evaluation_out(evaluation) if evaluation else None,
    )


async def _run_grading(submission_id: str, pyq: dict, answer_text: str, user_id: str) -> None:
    """Runs after the response has already gone back to the client."""
    await _db.answer_submissions.update_one(
        {"_id": ObjectId(submission_id)}, {"$set": {"status": "grading"}}
    )
    try:
        graded = await grade_answer(pyq, answer_text)
    except Exception:  # noqa: BLE001 — recorded on the submission, not raised into a response
        await _db.answer_submissions.update_one(
            {"_id": ObjectId(submission_id)}, {"$set": {"status": "grading_failed"}}
        )
        return

    evaluation_doc = {
        "submission_id": submission_id,
        "created_at": datetime.now(timezone.utc),
        **graded,
    }
    eval_result = await _db.answer_evaluations.insert_one(evaluation_doc)

    await _db.answer_submissions.update_one(
        {"_id": ObjectId(submission_id)}, {"$set": {"status": "graded"}}
    )

    if random.random() < MENTOR_SAMPLE_RATE:
        await _db.mentor_queue.insert_one(
            {
                "submission_id": submission_id,
                "evaluation_id": str(eval_result.inserted_id),
                "assigned_mentor_id": None,
                "sla_due_at": datetime.now(timezone.utc),
                "status": "pending",
            }
        )

    await notify(
        _db,
        user_id,
        NotificationType.evaluation_ready,
        "Your answer has been graded",
        f"Score: {graded['overall_score']}/{graded['max_marks']}. Open Practice to see feedback.",
    )


async def _create_submission(
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase,
    user: dict,
    pyq_id: str,
    answer_text: str,
    submission_type: str,
) -> AnswerSubmissionOut:
    pyq = await db.pyq_bank.find_one({"_id": ObjectId(pyq_id)})
    if not pyq:
        raise HTTPException(404, "Question not found")
    if pyq.get("options"):
        raise HTTPException(400, "This is an MCQ, not a descriptive Mains question")

    await check_and_consume_ai_quota(db, str(user["_id"]))

    now = datetime.now(timezone.utc)
    submission_doc = {
        "user_id": str(user["_id"]),
        "pyq_id": pyq_id,
        "answer_text": answer_text,
        "submission_type": submission_type,
        "status": "queued",
        "submitted_at": now,
    }
    result = await db.answer_submissions.insert_one(submission_doc)
    submission_id = str(result.inserted_id)

    background_tasks.add_task(_run_grading, submission_id, pyq, answer_text, str(user["_id"]))

    return AnswerSubmissionOut(
        id=submission_id,
        pyq_id=pyq_id,
        answer_text=answer_text,
        submission_type=submission_type,
        status="queued",
        submitted_at=now,
        evaluation=None,
    )


@router.post("/submit", response_model=AnswerSubmissionOut, status_code=202)
async def submit_answer(
    payload: AnswerSubmissionCreate,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    return await _create_submission(
        background_tasks, db, user, payload.pyq_id, payload.answer_text, "typed"
    )


@router.post("/submit-scan", response_model=AnswerSubmissionOut, status_code=202)
async def submit_scanned_answer(
    background_tasks: BackgroundTasks,
    pyq_id: str = Form(...),
    image: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """MOD-05's handwritten-scan intake path (Fig. 2). Transcribes via
    Claude vision (see services/ocr.py), then grades the transcript
    exactly like a typed submission."""
    if image.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(400, "Upload a JPEG, PNG, or WebP photo of the answer sheet")

    image_bytes = await image.read()
    try:
        answer_text = await transcribe_handwritten_answer(image_bytes, image.content_type)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"OCR transcription failed: {exc}") from exc

    if not answer_text:
        raise HTTPException(422, "Could not transcribe any text from that image")

    return await _create_submission(background_tasks, db, user, pyq_id, answer_text, "scanned")


@router.get("/{submission_id}", response_model=AnswerSubmissionOut)
async def get_submission(
    submission_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = await db.answer_submissions.find_one({"_id": ObjectId(submission_id)})
    if not doc or doc["user_id"] != str(user["_id"]):
        raise HTTPException(404, "Submission not found")

    evaluation = await db.answer_evaluations.find_one({"submission_id": submission_id})
    return _submission_out(doc, evaluation)
