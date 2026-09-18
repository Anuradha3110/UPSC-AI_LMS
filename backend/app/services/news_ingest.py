"""
MOD-03's daily current-affairs refresh. §12's live-news-wire line item
needs a paid vendor account (Dow Jones/Reuters-class feeds) this build
deliberately doesn't sign up for; Google News' public RSS search
(no key, no account) stands in as the real headline source instead.

Pipeline: RSS fetch -> validate -> dedupe (by URL, then by normalized
title within the run) -> one Claude tool-call per surviving headline that
both classifies UPSC relevance/category AND produces the exam pack
(summary, prelims facts, mains perspective, keywords, possible questions,
an optional MCQ) -> tag to syllabus nodes -> insert. Everything is
grounded only in the headline + publisher we actually have from the feed
— never inventing facts/figures the feed didn't provide.

All Claude calls go through services/anthropic_utils.create_message,
which runs the (synchronous) Anthropic client in a worker thread. That's
not a style choice: this project's AsyncAnthropic client hung
indefinitely on a real network call in this environment and froze the
whole server (including login) since the hang never yielded back to the
event loop. Do not swap these back to `AsyncAnthropic(...).messages.create`
without re-verifying that hang is gone.
"""
import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote
from xml.etree import ElementTree

import httpx
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings
from app.services.anthropic_utils import create_message
from app.services.tagging import tag_to_syllabus_nodes

logger = logging.getLogger("nirdesh.news_ingest")

# One query per GS-paper-ish beat so a day's digest spans the syllabus
# instead of whatever happened to trend. `when:1d` keeps each fetch to
# roughly the last 24 hours.
_FEED_QUERIES = [
    "India government policy OR parliament OR ministry",
    "India Supreme Court OR High Court judgment",
    "India economy OR RBI OR budget OR GST",
    "India environment OR climate OR wildlife conservation",
    "India science OR technology OR ISRO OR research",
    "India foreign policy OR diplomacy OR bilateral relations",
]
_ITEMS_PER_QUERY = 6

_CATEGORIES = [
    "polity_governance",
    "economy",
    "international_relations",
    "environment",
    "science_tech",
    "history_culture",
    "geography",
    "social_issues",
    "government_schemes",
    "defence",
    "reports_indices",
    "awards_appointments",
    "other",
]

_PROCESS_TOOL = {
    "name": "process_current_affairs_item",
    "description": "Classify a news headline for a UPSC Civil Services current-affairs digest and produce its exam-study pack.",
    "input_schema": {
        "type": "object",
        "properties": {
            "is_relevant": {
                "type": "boolean",
                "description": (
                    "True only if this genuinely matters for UPSC prep (polity, economy, "
                    "international relations, environment, science & tech, society, government "
                    "schemes, defence, reports/indices, awards, geography, history/culture). "
                    "False for pure sports scores, celebrity/entertainment gossip, crime blotter, "
                    "or purely local-interest items with no exam relevance."
                ),
            },
            "category": {"type": "string", "enum": _CATEGORIES},
            "summary": {
                "type": "string",
                "description": "2-4 plain sentences restating what the headline says, in fuller prose. Grounded only in the headline and publisher given — never invent facts, figures, or quotes.",
            },
            "prelims_facts": {
                "type": "array",
                "items": {"type": "string"},
                "description": "0-5 short standalone factual bullet points (dates, numbers, names, places) a Prelims aspirant should note — only facts actually present in the headline.",
            },
            "mains_perspective": {
                "type": "string",
                "description": "1-3 sentences on why this matters or what angle a Mains answer could take. Empty string if the headline is too thin for this.",
            },
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "3-6 short keyword/tag terms for this item.",
            },
            "possible_questions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "0-2 possible Mains-style question prompts this news could relate to.",
            },
            "mcq": {
                "type": "object",
                "description": "One Prelims-style MCQ, ONLY if the headline has enough concrete factual content to write a fair, unambiguous question. Omit this field entirely otherwise.",
                "properties": {
                    "question_text": {"type": "string"},
                    "options": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "label": {"type": "string"},
                                "text": {"type": "string"},
                            },
                            "required": ["label", "text"],
                        },
                    },
                    "correct_option": {"type": "string"},
                    "explanation": {"type": "string"},
                },
                "required": ["question_text", "options", "correct_option", "explanation"],
            },
        },
        "required": [
            "is_relevant",
            "category",
            "summary",
            "prelims_facts",
            "mains_perspective",
            "keywords",
            "possible_questions",
        ],
    },
}


def _feed_url(query: str) -> str:
    return f"https://news.google.com/rss/search?q={quote(query + ' when:1d')}&hl=en-IN&gl=IN&ceid=IN:en"


def _clean_title(title: str, source: str | None) -> str:
    suffix = f" - {source}"
    if source and title.endswith(suffix):
        return title[: -len(suffix)]
    return title


def _normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


async def _fetch_query(client: httpx.AsyncClient, query: str) -> list[dict]:
    try:
        resp = await client.get(_feed_url(query), timeout=10.0)
        resp.raise_for_status()
        root = ElementTree.fromstring(resp.text)
    except (httpx.HTTPError, ElementTree.ParseError) as exc:
        logger.warning("current-affairs feed fetch failed for %r: %s", query, exc)
        return []

    items = []
    for item in root.findall("./channel/item")[:_ITEMS_PER_QUERY]:
        link = (item.findtext("link") or "").strip()
        raw_title = (item.findtext("title") or "").strip()
        source = (item.findtext("source") or "").strip() or None
        pub_date_text = item.findtext("pubDate")
        if not link or not raw_title:
            continue
        try:
            published_at = parsedate_to_datetime(pub_date_text) if pub_date_text else None
        except (TypeError, ValueError):
            published_at = None
        if published_at and published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=timezone.utc)
        items.append(
            {
                "title": _clean_title(raw_title, source),
                "link": link,
                "source": source or "Google News",
                "published_at": published_at or datetime.now(timezone.utc),
            }
        )
    return items


def _as_string_list(value, limit: int) -> list[str]:
    """Defensively coerce a should-be array-of-strings tool field. Haiku
    occasionally mangles one of several sibling array fields in a single
    large tool call (seen in practice as a stray XML-ish fragment string
    instead of a JSON array) — never let that corrupt data reach Mongo, and
    never let it 500 the /digest endpoint for every reader."""
    if isinstance(value, list):
        return [str(v).strip() for v in value if isinstance(v, (str, int, float)) and str(v).strip()][:limit]
    return []


def _as_mcq(value) -> dict | None:
    if not isinstance(value, dict):
        return None
    options = value.get("options")
    if (
        not isinstance(value.get("question_text"), str)
        or not isinstance(options, list)
        or len(options) < 2
        or not isinstance(value.get("correct_option"), str)
        or not isinstance(value.get("explanation"), str)
    ):
        return None
    clean_options = [
        {"label": str(o.get("label")), "text": str(o.get("text"))}
        for o in options
        if isinstance(o, dict) and o.get("label") and o.get("text")
    ]
    if len(clean_options) < 2:
        return None
    return {
        "question_text": value["question_text"],
        "options": clean_options,
        "correct_option": value["correct_option"],
        "explanation": value["explanation"],
    }


async def _process_article(title: str, source: str) -> dict | None:
    """Classifies + produces the exam pack for one headline. Returns None
    on any failure (logged) so a single bad item can't abort the run."""
    try:
        response = await create_message(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            system=(
                "You process news headlines into a UPSC Civil Services current-affairs "
                "digest entry. You are given only a headline and its publisher — no "
                "article body. Call process_current_affairs_item. Never invent facts, "
                "figures, names, or quotes that aren't in the headline itself."
            ),
            tools=[_PROCESS_TOOL],
            tool_choice={"type": "tool", "name": "process_current_affairs_item"},
            messages=[{"role": "user", "content": f"Headline: {title}\nPublisher: {source}"}],
        )
        if response.stop_reason == "max_tokens":
            logger.warning("AI processing for %r hit max_tokens — output may be truncated", title)
        tool_use = next(b for b in response.content if b.type == "tool_use")
        raw = tool_use.input
        return {
            "is_relevant": bool(raw.get("is_relevant")),
            "category": raw.get("category") if isinstance(raw.get("category"), str) else None,
            "summary": raw.get("summary") if isinstance(raw.get("summary"), str) else "",
            "prelims_facts": _as_string_list(raw.get("prelims_facts"), 5),
            "mains_perspective": raw.get("mains_perspective") if isinstance(raw.get("mains_perspective"), str) else "",
            "keywords": _as_string_list(raw.get("keywords"), 6),
            "possible_questions": _as_string_list(raw.get("possible_questions"), 2),
            "mcq": _as_mcq(raw.get("mcq")),
        }
    except Exception:
        logger.exception("AI processing failed for %r", title)
        return None


async def ingest_current_affairs(
    db: AsyncIOMotorDatabase, max_items: int | None = None
) -> int:
    """Fetch today's headlines, dedupe against what's already stored and
    against each other, classify + process the survivors, and insert the
    UPSC-relevant ones as content_items. Returns the number inserted."""
    limit = max_items if max_items is not None else settings.news_max_items_per_run

    async with httpx.AsyncClient() as client:
        results = [await _fetch_query(client, q) for q in _FEED_QUERIES]

    by_link: dict[str, dict] = {}
    seen_titles: set[str] = set()
    for query_items in results:
        for it in query_items:
            if it["link"] in by_link:
                continue
            norm = _normalize_title(it["title"])
            if norm in seen_titles:
                continue
            seen_titles.add(norm)
            by_link[it["link"]] = it

    inserted = 0
    skipped_irrelevant = 0
    for link, item in by_link.items():
        if inserted >= limit:
            break
        if await db.content_items.find_one({"source_url": link}):
            continue

        processed = await _process_article(item["title"], item["source"])
        if processed is None:
            continue
        if not processed.get("is_relevant"):
            skipped_irrelevant += 1
            continue

        body = processed.get("summary", "").strip()
        if not body:
            continue

        node_ids = await tag_to_syllabus_nodes(db, item["title"], body)
        mcq = processed.get("mcq") or None
        category = processed.get("category")
        if category not in _CATEGORIES:
            category = "other"

        doc = {
            "title": item["title"],
            "body": body,
            "source_type": "derived_summary",
            "source_url": link,
            "source_name": item["source"],
            "syllabus_node_ids": node_ids,
            "tags": processed.get("keywords", []),
            "is_current_affairs": True,
            "published_at": item["published_at"],
            "category": category,
            "prelims_facts": processed.get("prelims_facts", []),
            "mains_perspective": processed.get("mains_perspective") or None,
            "possible_questions": processed.get("possible_questions", []),
            "mcq": mcq,
        }
        await db.content_items.insert_one(doc)
        inserted += 1

    logger.info(
        "current-affairs ingest: %d new item(s) added, %d skipped as not UPSC-relevant",
        inserted,
        skipped_irrelevant,
    )
    return inserted
