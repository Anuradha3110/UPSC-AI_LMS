"""
Idempotent demo-data seed: one user per role, a small GS2 syllabus slice,
and a handful of PYQs — enough to exercise auth, the syllabus API, and a
real Prelims mock test end to end.

Run with:  python -m app.seed
"""
import asyncio

from app.core.database import db
from app.core.security import hash_password

DEMO_PASSWORD = "Nirdesh@2026"


async def seed_users():
    users = [
        {"name": "Demo Aspirant", "email": "aspirant@demo.com", "role": "aspirant",
         "optional_subject": "Public Administration"},
        {"name": "Demo Mentor", "email": "mentor@demo.com", "role": "mentor",
         "optional_subject": None},
        {"name": "Demo Editor", "email": "editor@demo.com", "role": "content_editor",
         "optional_subject": None},
        {"name": "Demo Admin", "email": "admin@demo.com", "role": "admin",
         "optional_subject": None},
    ]
    for u in users:
        exists = await db.users.find_one({"email": u["email"]})
        if exists:
            continue
        await db.users.insert_one({**u, "password_hash": hash_password(DEMO_PASSWORD)})
    print(f"Seeded {len(users)} demo users (password: {DEMO_PASSWORD})")


async def seed_syllabus():
    nodes = [
        {"paper": "GS2", "title": "Indian Polity", "parent_id": None,
         "tags": ["polity"], "optional_subject": None},
        {"paper": "GS2", "title": "Fundamental Rights", "parent_id": None,
         "tags": ["polity", "constitution"], "optional_subject": None},
        {"paper": "GS3", "title": "Indian Economy", "parent_id": None,
         "tags": ["economy"], "optional_subject": None},
    ]
    node_ids = {}
    for n in nodes:
        existing = await db.syllabus_nodes.find_one({"paper": n["paper"], "title": n["title"]})
        if existing:
            node_ids[n["title"]] = existing["_id"]
            continue
        result = await db.syllabus_nodes.insert_one(n)
        node_ids[n["title"]] = result.inserted_id
    print(f"Seeded {len(nodes)} syllabus nodes")
    return node_ids


async def seed_pyqs(node_ids: dict):
    fr_id = str(node_ids["Fundamental Rights"])

    mcqs = [
        {
            "year": 2023, "paper": "GS1", "marks": 2,
            "question_text": "Which Article of the Indian Constitution abolishes untouchability?",
            "syllabus_node_ids": [fr_id],
            "options": [
                {"label": "A", "text": "Article 14"},
                {"label": "B", "text": "Article 15"},
                {"label": "C", "text": "Article 17"},
                {"label": "D", "text": "Article 19"},
            ],
            "correct_option": "C",
        },
        {
            "year": 2022, "paper": "CSAT", "marks": 2.5,
            "question_text": "If a train 120m long crosses a pole in 10 seconds, its speed is:",
            "syllabus_node_ids": [],
            "options": [
                {"label": "A", "text": "12 km/h"},
                {"label": "B", "text": "43.2 km/h"},
                {"label": "C", "text": "36 km/h"},
                {"label": "D", "text": "48 km/h"},
            ],
            "correct_option": "B",
        },
        {
            # descriptive Mains entry — no options; this is what MOD-05's
            # rubric retrieval will pull a marking scheme from later
            "year": 2023, "paper": "GS2", "marks": 15,
            "question_text": "Discuss the significance of Fundamental Rights as a check on "
                              "arbitrary state action, with reference to recent judicial pronouncements.",
            "syllabus_node_ids": [fr_id],
            "options": None,
            "correct_option": None,
            "marking_scheme": "Intro: define FRs as justiciable rights under Part III. "
                               "Body: separate dimensions — legislative check, executive check, "
                               "judicial review (cite 2-3 recent judgments). Conclusion: balance "
                               "with reasonable restrictions. Word limit 250.",
        },
    ]

    inserted = 0
    for q in mcqs:
        exists = await db.pyq_bank.find_one(
            {"question_text": q["question_text"], "year": q["year"]}
        )
        if exists:
            continue
        await db.pyq_bank.insert_one(q)
        inserted += 1
    print(f"Seeded {inserted} PYQ bank entries")


async def main():
    await seed_users()
    node_ids = await seed_syllabus()
    await seed_pyqs(node_ids)


if __name__ == "__main__":
    asyncio.run(main())
