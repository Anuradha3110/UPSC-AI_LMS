"""
MOD-02 — Curriculum & Syllabus Graph. Read access is open to any
authenticated context (the marketing site also browses it read-only for
SEO pages); writes are locked to content_editor/admin — the role-gating
TODO this router used to carry is now closed via `require_role`.
"""
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.deps import require_role
from app.models.syllabus import Paper, SyllabusNodeCreate, SyllabusNodeOut

router = APIRouter()


def _to_out(doc: dict) -> SyllabusNodeOut:
    return SyllabusNodeOut(
        id=str(doc["_id"]),
        paper=doc["paper"],
        title=doc["title"],
        parent_id=doc.get("parent_id"),
        tags=doc.get("tags", []),
        optional_subject=doc.get("optional_subject"),
    )


@router.get("", response_model=list[SyllabusNodeOut])
async def list_nodes(
    paper: Paper | None = Query(default=None),
    optional_subject: str | None = Query(default=None),
    parent_id: str | None = Query(default=None),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    query: dict = {}
    if paper:
        query["paper"] = paper.value
    if optional_subject:
        query["optional_subject"] = optional_subject
    if parent_id is not None:
        query["parent_id"] = parent_id if parent_id != "" else None
    docs = await db.syllabus_nodes.find(query).to_list(length=2000)
    return [_to_out(d) for d in docs]


@router.get("/optional-subjects", response_model=list[str])
async def list_optional_subjects(db: AsyncIOMotorDatabase = Depends(get_db)):
    subjects = await db.syllabus_nodes.distinct("optional_subject", {"paper": "OPTIONAL"})
    return sorted(s for s in subjects if s)


@router.post("", response_model=SyllabusNodeOut, status_code=201)
async def create_node(
    payload: SyllabusNodeCreate,
    _user: dict = Depends(require_role("content_editor", "admin")),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    doc = payload.model_dump()
    result = await db.syllabus_nodes.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_out(doc)
