"""
Manual/on-demand run of the daily current-affairs refresh (normally run
automatically by main.py's startup loop every 24h — see services/news_ingest.py
for why Google News RSS stands in for a paid news-wire API here).

Run with:  python -m app.ingest_current_affairs
"""
import asyncio

from app.core.database import db
from app.services.news_ingest import ingest_current_affairs


async def main():
    count = await ingest_current_affairs(db)
    print(f"current-affairs ingest: {count} new item(s) added")


if __name__ == "__main__":
    asyncio.run(main())
