"""
MOD-07 — conceptual doubt-resolution half. §06's "retrieval before
scoring" principle applies here too: retrieve candidate content_items by
simple text search first, hand the retrieved passages to Claude as its
only grounding, and require it to cite which passage backed each claim
so "an aspirant can check the claim, not just trust it." Low-confidence
or zero-retrieval answers escalate to a human mentor automatically.
"""
from anthropic import AsyncAnthropic
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


_ANSWER_TOOL = {
    "name": "record_answer",
    "description": "Record an answer to the aspirant's conceptual doubt, grounded only in the provided passages.",
    "input_schema": {
        "type": "object",
        "properties": {
            "answer": {"type": "string", "description": "2-6 sentence answer."},
            "cited_passage_indexes": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "0-based indexes of the passages actually used to ground the answer.",
            },
            "confidence": {
                "type": "string",
                "enum": ["high", "low"],
                "description": "'low' if the provided passages don't really cover this doubt — the answer will still be shown, but the doubt auto-escalates to a mentor.",
            },
        },
        "required": ["answer", "cited_passage_indexes", "confidence"],
    },
}


async def resolve_doubt(db: AsyncIOMotorDatabase, question_text: str, syllabus_node_id: str | None) -> dict:
    # Prefer an explicit syllabus-node filter; fall back to full-text search
    # over content_items; fall back to a small unfiltered sample so the
    # model always has *something* to ground against (and can say "low
    # confidence, these don't cover it" rather than hallucinating from nothing).
    passages: list[dict] = []
    if syllabus_node_id:
        passages = await db.content_items.find({"syllabus_node_ids": syllabus_node_id}).limit(5).to_list(length=5)
    if not passages and await _has_text_index(db):
        passages = await db.content_items.find({"$text": {"$search": question_text}}).limit(5).to_list(length=5)
    if not passages:
        passages = await db.content_items.find({}).limit(5).to_list(length=5)

    if not passages:
        return {
            "ai_answer": None,
            "citations": [],
            "confidence": "low",
        }

    passage_block = "\n\n".join(
        f"[{i}] {p['title']}: {p['body'][:800]}" for i, p in enumerate(passages)
    )

    client = _get_client()
    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=768,
        system=(
            "Answer the aspirant's UPSC-prep doubt using ONLY the passages below. "
            "If they don't actually answer it, say so plainly and set confidence to low. "
            "Call record_answer."
        ),
        tools=[_ANSWER_TOOL],
        tool_choice={"type": "tool", "name": "record_answer"},
        messages=[{"role": "user", "content": f"Doubt: {question_text}\n\nPassages:\n{passage_block}"}],
    )
    tool_use = next(b for b in response.content if b.type == "tool_use")
    data = tool_use.input

    citations = [
        {
            "content_item_id": str(passages[i]["_id"]),
            "title": passages[i]["title"],
            "excerpt": passages[i]["body"][:300],
        }
        for i in data.get("cited_passage_indexes", [])
        if 0 <= i < len(passages)
    ]

    return {
        "ai_answer": data["answer"],
        "citations": citations,
        "confidence": data["confidence"],
    }


async def _has_text_index(db: AsyncIOMotorDatabase) -> bool:
    indexes = await db.content_items.index_information()
    return any(idx.get("weights") or idx.get("textIndexVersion") for idx in indexes.values())
