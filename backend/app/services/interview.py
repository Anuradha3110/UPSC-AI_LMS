"""
MOD-08 — Personality Test Simulator. Text-based panel round only in
this build (voice articulation is the §12 Phase-4 extension). One
Claude call per turn, conditioned on the DAF snapshot and the transcript
so far; a separate closing call produces feedback once the aspirant ends
the session.
"""
from anthropic import AsyncAnthropic

from app.core.config import settings
from app.services.anthropic_utils import first_text

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


def _daf_block(daf: dict) -> str:
    return (
        f"Cadre preference: {', '.join(daf.get('cadre_preference', [])) or 'not stated'}\n"
        f"Optional subject: {daf.get('optional_subject')}\n"
        f"Hobbies: {', '.join(daf.get('hobbies', [])) or 'not stated'}\n"
        f"Work experience: {daf.get('work_experience') or 'none stated'}\n"
        f"Home district/state: {daf.get('home_district')}, {daf.get('home_state')}\n"
        f"Graduation field: {daf.get('graduation_field') or 'not stated'}"
    )


async def next_panel_turn(daf: dict, transcript: list[dict]) -> str:
    history = "\n".join(f"{t['role'].upper()}: {t['text']}" for t in transcript) or "(session just started)"
    client = _get_client()
    response = await client.messages.create(
        model=settings.grading_model,
        max_tokens=400,
        system=(
            "You are a 3-member UPSC Civil Services Board panel conducting a Personality "
            "Test interview. Ask ONE question at a time, grounded in the candidate's DAF "
            "below — probe their optional subject, hobbies, work experience, home district "
            "current affairs, and cadre preference with realistic follow-ups. Stay in character "
            "as the panel; do not narrate stage directions.\n\n"
            f"Candidate DAF:\n{_daf_block(daf)}"
        ),
        messages=[{"role": "user", "content": f"Interview so far:\n{history}\n\nAsk the next question."}],
    )
    return first_text(response)


async def close_out_feedback(daf: dict, transcript: list[dict]) -> str:
    history = "\n".join(f"{t['role'].upper()}: {t['text']}" for t in transcript)
    client = _get_client()
    response = await client.messages.create(
        model=settings.grading_model,
        max_tokens=600,
        system=(
            "You are the panel chair. The interview has ended. Give the candidate direct, "
            "constructive feedback: 2-3 strengths, 2-3 areas to work on before the real "
            "interview, and one overall readiness note. No score — UPSC panels don't disclose one."
        ),
        messages=[{"role": "user", "content": f"Candidate DAF:\n{_daf_block(daf)}\n\nFull transcript:\n{history}"}],
    )
    return first_text(response)
