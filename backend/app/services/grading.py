"""
MOD-05 core: §06's "Rubric Retrieval -> LLM Scoring" steps. Rubric
retrieval here is a direct lookup of the PYQ's own `marking_scheme` field
(seeded in app/seed.py) rather than a vector search — that's the
Phase-2+ upgrade once the PYQ bank is large enough that not every
question has a hand-written scheme attached.

Word count is computed here in Python and handed to the model as a
fact, not left for the model to count itself — LLMs are unreliable at
counting words in their own input, so word_limit_adherence would be
scoring against a guess otherwise.
"""
from anthropic import AsyncAnthropic

from app.core.config import settings

RUBRIC_VERSION = "v1"

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set — cannot grade answers")
        _client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


def expected_word_limit(marks: float) -> int:
    """Mirrors the word limits printed on the real UPSC Mains question paper."""
    if marks >= 100:
        return 1200  # Essay-length response
    if marks >= 15:
        return 250
    if marks >= 10:
        return 150
    return 100


_EVALUATION_TOOL = {
    "name": "record_evaluation",
    "description": "Record a UPSC Mains examiner's score for one descriptive answer.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "content_coverage": {
                "type": "integer",
                "description": "0-10: how fully the answer covers what the marking scheme demands.",
            },
            "structure": {
                "type": "integer",
                "description": "0-10: intro-body-conclusion discipline and paragraphing appropriate to a Mains answer.",
            },
            "word_limit_adherence": {
                "type": "integer",
                "description": "0-10, based on the word-count-vs-limit figures given to you. Penalize both padding past the limit and being too thin.",
            },
            "value_addition": {
                "type": "integer",
                "description": "0-10: use of examples, data, committee/report references, or current-affairs linkage beyond bare syllabus recall.",
            },
            "overall_score": {
                "type": "number",
                "description": "Final mark out of max_marks — your holistic judgment, not required to equal the average of the four dimensions.",
            },
            "feedback_text": {
                "type": "string",
                "description": "2-5 sentences of specific, actionable feedback the aspirant can act on next attempt.",
            },
        },
        "required": [
            "content_coverage",
            "structure",
            "word_limit_adherence",
            "value_addition",
            "overall_score",
            "feedback_text",
        ],
        "additionalProperties": False,
    },
}


async def grade_answer(pyq: dict, answer_text: str) -> dict:
    marks = pyq["marks"]
    word_count = len(answer_text.split())
    limit = expected_word_limit(marks)
    marking_scheme = pyq.get("marking_scheme") or "No official marking scheme on file — grade against general UPSC Mains conventions for this GS paper."

    system = (
        "You are a UPSC Civil Services Mains examiner. Score the aspirant's answer "
        "strictly against the marking scheme below — do not reward fluent writing "
        "that skips the scheme's required dimensions, and do not penalize a plain "
        "style that hits every required point.\n\n"
        f"Question ({pyq['paper']}, {marks} marks): {pyq['question_text']}\n\n"
        f"Marking scheme: {marking_scheme}\n\n"
        f"Word limit: {limit}. The aspirant's answer is {word_count} words.\n\n"
        "Call record_evaluation with your scores."
    )

    client = _get_client()
    response = await client.messages.create(
        model=settings.grading_model,
        max_tokens=2048,
        system=system,
        tools=[_EVALUATION_TOOL],
        tool_choice={"type": "tool", "name": "record_evaluation"},
        messages=[{"role": "user", "content": answer_text}],
    )

    tool_use = next(b for b in response.content if b.type == "tool_use")
    data = tool_use.input

    return {
        "rubric_version": RUBRIC_VERSION,
        "dimension_scores": {
            "content_coverage": data["content_coverage"],
            "structure": data["structure"],
            "word_limit_adherence": data["word_limit_adherence"],
            "value_addition": data["value_addition"],
        },
        "overall_score": min(float(data["overall_score"]), marks),
        "max_marks": marks,
        "feedback_text": data["feedback_text"],
        "word_count": word_count,
        "expected_word_limit": limit,
    }
