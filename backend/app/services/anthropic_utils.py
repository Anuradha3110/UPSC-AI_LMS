"""
Shared helpers for services/*.py that call the Claude API directly.
"""
import asyncio

from anthropic import Anthropic

from app.core.config import settings

_sync_client: Anthropic | None = None


def _get_sync_client() -> Anthropic:
    global _sync_client
    if _sync_client is None:
        _sync_client = Anthropic(api_key=settings.anthropic_api_key)
    return _sync_client


async def create_message(**kwargs):
    """Same call signature as `client.messages.create(**kwargs)`, but runs
    the (synchronous) Claude call in a worker thread via `asyncio.to_thread`.

    Why: this project's `AsyncAnthropic` client hung indefinitely on a real
    network call in this environment (traced to the `httpx2`-based async
    transport it now depends on) — and because that hang never yields back
    to the event loop, it froze the *entire* FastAPI server, including
    unrelated requests like login. Running the sync client in a real OS
    thread means the worst case is one leaked background thread, not a
    dead server. Use this instead of an `AsyncAnthropic` client for any new
    call site."""
    client = _get_sync_client()
    return await asyncio.to_thread(client.messages.create, **kwargs)


def first_text(response) -> str:
    """`response.content[0]` isn't reliably the text block — extended
    thinking models put a ThinkingBlock first. Find the first TextBlock
    instead."""
    for block in response.content:
        if block.type == "text":
            return block.text
    raise RuntimeError("No text block in Claude's response")
