"""
Loads every subject/paper JSON file under app/data/subjects/ (schema in
app/data/SCHEMA.md) plus app/data/current_affairs.json into Mongo.
Idempotent: re-running updates existing docs (matched by natural key)
instead of duplicating them, so it's safe to re-run after adding a new
subject file or editing an existing one.

Run with:  python -m app.seed_content
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path

from app.core.database import db
from app.services.tagging import tag_to_syllabus_nodes

DATA_DIR = Path(__file__).parent / "data"


async def load_subject_file(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    paper = data["paper"]
    optional_subject = data.get("optional_subject")

    # 1) syllabus_nodes — insert parents before children, tracking title -> _id
    title_to_id: dict[str, str] = {}
    nodes = data["syllabus_nodes"]
    remaining = list(nodes)
    # simple two-pass resolution: top-level first, then anything whose parent is already resolved
    while remaining:
        progressed = False
        still_remaining = []
        for n in remaining:
            parent_title = n.get("parent_title")
            if parent_title is not None and parent_title not in title_to_id:
                still_remaining.append(n)
                continue
            doc = {
                "paper": paper,
                "title": n["title"],
                "parent_id": title_to_id.get(parent_title) if parent_title else None,
                "tags": n.get("tags", []),
                "optional_subject": optional_subject,
            }
            existing = await db.syllabus_nodes.find_one({"paper": paper, "title": n["title"], "optional_subject": optional_subject})
            if existing:
                await db.syllabus_nodes.update_one({"_id": existing["_id"]}, {"$set": doc})
                title_to_id[n["title"]] = str(existing["_id"])
            else:
                result = await db.syllabus_nodes.insert_one(doc)
                title_to_id[n["title"]] = str(result.inserted_id)
            progressed = True
        if not progressed:
            # a parent_title didn't match any node in this file — treat remaining as top-level
            for n in still_remaining:
                doc = {
                    "paper": paper, "title": n["title"], "parent_id": None,
                    "tags": n.get("tags", []), "optional_subject": optional_subject,
                }
                result = await db.syllabus_nodes.insert_one(doc)
                title_to_id[n["title"]] = str(result.inserted_id)
            break
        remaining = still_remaining

    # 2) pyqs
    pyq_count = 0
    for p in data.get("pyqs", []):
        node_ids = [title_to_id[t] for t in p.get("node_titles", []) if t in title_to_id]
        doc = {
            "year": p["year"],
            "paper": paper,
            "question_text": p["question_text"],
            "marks": p["marks"],
            "syllabus_node_ids": node_ids,
            "optional_subject": optional_subject,
            "options": p.get("options"),
            "correct_option": p.get("correct_option"),
            "marking_scheme": p.get("marking_scheme"),
        }
        existing = await db.pyq_bank.find_one(
            {"question_text": doc["question_text"], "year": doc["year"], "paper": paper}
        )
        if existing:
            await db.pyq_bank.update_one({"_id": existing["_id"]}, {"$set": doc})
        else:
            await db.pyq_bank.insert_one(doc)
        pyq_count += 1

    # 3) content_items
    content_count = 0
    for c in data.get("content_items", []):
        node_ids = [title_to_id[t] for t in c.get("node_titles", []) if t in title_to_id]
        doc = {
            "title": c["title"],
            "body": c["body"],
            "source_type": c["source_type"],
            "source_url": c.get("source_url"),
            "syllabus_node_ids": node_ids,
            "tags": c.get("tags", []),
            "is_current_affairs": c.get("is_current_affairs", False),
            "published_at": c.get("published_at"),
        }
        existing = await db.content_items.find_one({"title": doc["title"]})
        if existing:
            await db.content_items.update_one({"_id": existing["_id"]}, {"$set": doc})
        else:
            await db.content_items.insert_one(doc)
        content_count += 1

    print(f"{path.name}: {len(title_to_id)} nodes, {pyq_count} pyqs, {content_count} content items")


def _parse_published_at(raw) -> datetime | None:
    """The JSON seed files carry published_at as an ISO-8601 string (e.g.
    "2026-09-05T00:00:00Z") — parse it into a real datetime before it goes
    into Mongo. Storing it as a raw string (the original bug here) makes
    every date-range query silently match nothing, since Mongo can't
    range-compare a string against a datetime cutoff."""
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw
    return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))


async def load_current_affairs(path: Path) -> None:
    if not path.exists():
        print("current_affairs.json not found — skipping")
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    count = 0
    for c in data.get("content_items", []):
        published_at = _parse_published_at(c.get("published_at"))
        existing = await db.content_items.find_one({"title": c["title"]})
        if existing:
            # backfill: earlier runs of this script stored published_at as a
            # raw string before this fix — repair it in place if so.
            if isinstance(existing.get("published_at"), str):
                await db.content_items.update_one(
                    {"_id": existing["_id"]}, {"$set": {"published_at": published_at}}
                )
            continue
        node_ids = await tag_to_syllabus_nodes(db, c["title"], c["body"])
        doc = {
            "title": c["title"],
            "body": c["body"],
            "source_type": c["source_type"],
            "source_url": c.get("source_url"),
            "syllabus_node_ids": node_ids,
            "tags": c.get("tags", []),
            "is_current_affairs": True,
            "published_at": published_at,
        }
        await db.content_items.insert_one(doc)
        count += 1
    print(f"current_affairs.json: {count} new items tagged via AI classification and inserted")


async def main():
    subjects_dir = DATA_DIR / "subjects"
    files = sorted(subjects_dir.glob("*.json"))
    print(f"Found {len(files)} subject files")
    for f in files:
        try:
            await load_subject_file(f)
        except Exception as exc:  # noqa: BLE001 — keep loading the rest even if one file is malformed
            print(f"{f.name}: FAILED — {exc}")

    await load_current_affairs(DATA_DIR / "current_affairs.json")


if __name__ == "__main__":
    asyncio.run(main())
