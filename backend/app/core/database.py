"""
One Motor client for the whole app (§08 of the architecture: one database
story). Collections referenced elsewhere match the names in §07's data
architecture table — keep new collections consistent with that table.
"""
from urllib.parse import urlparse

import dns.resolver
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings


def _resolve_srv_uri(uri: str) -> str:
    """On this machine Windows hands the OS resolver a link-local IPv6 DNS
    server (fe80::1) that flakes on the mongodb+srv:// SRV/TXT lookups
    pymongo does internally, causing connects/queries to hang intermittently.
    Resolving SRV+TXT ourselves against public DNS and building a direct
    mongodb:// URI sidesteps the driver's own (unreliable) SRV resolution."""
    if not uri.startswith("mongodb+srv://"):
        return uri

    parsed = urlparse(uri)
    host = parsed.hostname
    resolver = dns.resolver.Resolver()
    resolver.nameservers = ["8.8.8.8", "1.1.1.1"]

    srv_records = resolver.resolve(f"_mongodb._tcp.{host}", "SRV")
    hosts = ",".join(
        f"{r.target.to_text().rstrip('.')}:{r.port}" for r in srv_records
    )

    try:
        txt_records = resolver.resolve(host, "TXT")
        txt_params = "&".join(
            b"".join(r.strings).decode() for r in txt_records
        )
    except dns.resolver.NoAnswer:
        txt_params = ""

    userinfo = ""
    if parsed.username:
        userinfo = parsed.username
        if parsed.password:
            userinfo += f":{parsed.password}"
        userinfo += "@"

    query = "tls=true"
    if txt_params:
        query += f"&{txt_params}"
    if parsed.query:
        query += f"&{parsed.query}"

    path = parsed.path or ""
    return f"mongodb://{userinfo}{hosts}{path}?{query}"


_client: AsyncIOMotorClient = AsyncIOMotorClient(_resolve_srv_uri(settings.mongodb_uri))
db: AsyncIOMotorDatabase = _client[settings.mongodb_db]


def get_db() -> AsyncIOMotorDatabase:
    """FastAPI dependency — inject with `db=Depends(get_db)`."""
    return db


async def ensure_indexes() -> None:
    """Called once from main.py's startup event. Most important: the text
    index on content_items — without it, services/doubts.py's full-text
    search silently never matches anything and every doubt falls back to
    an arbitrary unfiltered sample of reading material."""
    await db.content_items.create_index([("title", "text"), ("body", "text")])
    await db.users.create_index("email", unique=True)
    await db.pyq_bank.create_index([("paper", 1), ("options", 1)])
    await db.revision_schedule.create_index([("user_id", 1), ("syllabus_node_id", 1)], unique=True)
    await db.subscriptions.create_index("user_id", unique=True)
    await db.daf_profiles.create_index("user_id", unique=True)
    await db.bookmarks.create_index([("user_id", 1), ("content_item_id", 1)], unique=True)
    await db.annotations.create_index([("user_id", 1), ("content_item_id", 1)])
    await db.reading_progress.create_index([("user_id", 1), ("content_item_id", 1)], unique=True)
