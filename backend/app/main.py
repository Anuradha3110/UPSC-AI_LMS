import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router as api_v1_router
from app.core.config import settings
from app.core.database import db, ensure_indexes

logger = logging.getLogger("nirdesh.main")

app = FastAPI(title="Nirdesh API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    # Next.js dev bumps to the next free port (3001, 3002, ...) whenever an
    # earlier dev server is still holding the previous one — allowlisting
    # specific ports in CORS_ORIGINS keeps breaking as that drifts, so any
    # localhost port is trusted in addition to the explicit list above.
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router)

_news_task: asyncio.Task | None = None

DAY_SECONDS = 24 * 60 * 60


async def _daily_news_loop() -> None:
    """Runs for as long as the server does — one ingest now, then one
    every 24h. A failed run (feed down, API hiccup) just gets logged and
    retried on the next tick rather than killing the loop."""
    from app.services.news_ingest import ingest_current_affairs

    while True:
        try:
            await ingest_current_affairs(db)
        except Exception:
            logger.exception("current-affairs ingest failed")
        await asyncio.sleep(DAY_SECONDS)


@app.on_event("startup")
async def _startup() -> None:
    await ensure_indexes()
    global _news_task
    if settings.news_ingest_enabled:
        _news_task = asyncio.create_task(_daily_news_loop())


@app.on_event("shutdown")
async def _shutdown() -> None:
    if _news_task is not None:
        _news_task.cancel()


@app.get("/health")
async def health():
    return {"status": "ok"}
