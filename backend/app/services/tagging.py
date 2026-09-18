"""
MOD-02/03's "AI touchpoint": auto-tag a piece of content to syllabus
nodes. The architecture (§04/§07) specs this as Atlas Vector Search
embedding similarity; this build uses a one-shot Claude classification
call against the candidate node titles instead — no embeddings pipeline
or Atlas Search index to stand up, same "not manually filed" outcome.
Swap this for real vector search once content volume makes a
classification call per item too slow/expensive.
"""
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.anthropic_utils import create_message

_TAG_TOOL = {
    "name": "record_tags",
    "description": "Record which syllabus nodes a piece of content belongs to.",
    "input_schema": {
        "type": "object",
        "properties": {
            "node_titles": {
                "type": "array",
                "items": {"type": "string"},
                "description": "0-5 node titles from the candidate list that this content is actually about. Empty if none fit well.",
            }
        },
        "required": ["node_titles"],
    },
}


async def tag_to_syllabus_nodes(db: AsyncIOMotorDatabase, title: str, body: str) -> list[str]:
    """Returns syllabus_node ids the content was matched to."""
    candidates = await db.syllabus_nodes.find({}, {"title": 1}).to_list(length=1000)
    if not candidates:
        return []

    title_to_id = {c["title"]: str(c["_id"]) for c in candidates}
    candidate_list = "\n".join(f"- {t}" for t in title_to_id)

    response = await create_message(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=(
            "Match the given content to the most relevant UPSC syllabus node "
            "titles from the candidate list. Call record_tags."
        ),
        tools=[_TAG_TOOL],
        tool_choice={"type": "tool", "name": "record_tags"},
        messages=[
            {
                "role": "user",
                "content": f"Title: {title}\n\nBody: {body[:2000]}\n\nCandidate syllabus nodes:\n{candidate_list}",
            }
        ],
    )
    tool_use = next(b for b in response.content if b.type == "tool_use")
    matched_titles = tool_use.input.get("node_titles", [])
    return [title_to_id[t] for t in matched_titles if t in title_to_id]
