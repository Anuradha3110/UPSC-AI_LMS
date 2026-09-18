"""
MOD-09 — Analytics & Progress Intelligence. Three things: a weak-topic
heatmap from graded Mains answers, a rough percentile-vs-cutoff estimate
from Prelims mock attempts, and mentor-override rate per rubric_version
— the grading-quality trend line §09/§13 both name as a first-class
metric, not an afterthought.
"""
from bson import ObjectId
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.deps import get_current_user, require_role

router = APIRouter()

# Rough historical Prelims GS1 cutoff band (raw marks out of 200) — used only
# to give a directional percentile estimate, not a guaranteed prediction.
_HISTORICAL_CUTOFF_BAND = {"low": 88, "mid": 100, "high": 115}


@router.get("/me/weak-topics")
async def weak_topics(
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    submissions = await db.answer_submissions.find(
        {"user_id": str(user["_id"]), "status": "graded"}
    ).to_list(length=500)

    node_scores: dict[str, list[float]] = {}
    for sub in submissions:
        pyq = await db.pyq_bank.find_one({"_id": ObjectId(sub["pyq_id"])})
        if not pyq or not pyq.get("syllabus_node_ids"):
            continue
        evaluation = await db.answer_evaluations.find_one({"submission_id": str(sub["_id"])})
        if not evaluation or not evaluation.get("max_marks"):
            continue
        ratio = evaluation["overall_score"] / evaluation["max_marks"]
        for node_id in pyq["syllabus_node_ids"]:
            node_scores.setdefault(node_id, []).append(ratio)

    heatmap = []
    for node_id, ratios in node_scores.items():
        node = await db.syllabus_nodes.find_one({"_id": ObjectId(node_id)})
        heatmap.append(
            {
                "syllabus_node_id": node_id,
                "syllabus_node_title": node["title"] if node else "(deleted node)",
                "avg_score_ratio": round(sum(ratios) / len(ratios), 3),
                "attempts": len(ratios),
            }
        )
    heatmap.sort(key=lambda h: h["avg_score_ratio"])
    return heatmap


@router.get("/me/prelims-percentile")
async def prelims_percentile(
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    attempts = (
        await db.test_attempts.find({"user_id": str(user["_id"]), "paper": "GS1"})
        .sort("raw_score", -1)
        .to_list(length=1)
    )
    if not attempts:
        return {"estimate": None, "message": "No GS1 mock attempts recorded yet"}

    score = attempts[0]["raw_score"]
    band = _HISTORICAL_CUTOFF_BAND
    if score >= band["high"]:
        read = "comfortably above the historical GS1 cutoff band"
    elif score >= band["mid"]:
        read = "around the historical GS1 cutoff band"
    elif score >= band["low"]:
        read = "near the lower edge of the historical GS1 cutoff band"
    else:
        read = "below the historical GS1 cutoff band"

    return {
        "latest_raw_score": score,
        "historical_cutoff_band": band,
        "read": read,
    }


@router.get("/mentor-override-rate")
async def mentor_override_rate(
    _user: dict = Depends(require_role("mentor", "admin")),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    reviewed = await db.mentor_queue.find({"status": "reviewed"}).to_list(length=5000)
    by_version: dict[str, dict[str, int]] = {}
    for item in reviewed:
        evaluation = await db.answer_evaluations.find_one({"_id": ObjectId(item["evaluation_id"])})
        if not evaluation:
            continue
        version = evaluation["rubric_version"]
        bucket = by_version.setdefault(version, {"reviewed": 0, "overridden": 0})
        bucket["reviewed"] += 1
        if evaluation.get("mentor_override"):
            bucket["overridden"] += 1

    return [
        {
            "rubric_version": v,
            "reviewed": b["reviewed"],
            "overridden": b["overridden"],
            "override_rate": round(b["overridden"] / b["reviewed"], 3) if b["reviewed"] else 0,
        }
        for v, b in by_version.items()
    ]
