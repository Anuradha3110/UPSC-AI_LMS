# Nirdesh — UPSC AI LMS

A functional-prototype build of every module in **Project Nirdesh — System
Architecture v1.0** (the published artifact — find it via `Artifact` action
"list" in the conversation that scaffolded this, or ask for the link). All
five roadmap phases (§12) have a working vertical slice; the notes below say
exactly what's real vs. mocked so nothing here is mistaken for more finished
than it is.

## What "functional prototype" means here

Per an explicit build decision: every module's core logic is real, working
code against real seed data, but external infrastructure that would need a
live account or a provisioned server is substituted with a local/mocked
equivalent so the whole platform runs end-to-end without extra signups:

| Architecture spec | This build |
|---|---|
| Redis + worker pool grading queue (§08/§10) | FastAPI `BackgroundTasks` — same "queued, not inline" contract, no Redis to run |
| Paid news-wire API for the current-affairs digest | Google News RSS (free, no key) + a Claude-written summary, refreshed automatically every 24h (`services/news_ingest.py`) |
| Dedicated OCR vendor for handwritten scans | Claude vision transcribes the photo directly (`services/ocr.py`) |
| Atlas Vector Search embeddings for content tagging | A one-shot Claude classification call against candidate syllabus nodes (`services/tagging.py`) |
| Razorpay live payments | Active Razorpay Payment Gateway SDK with HMAC signature verification & webhook support (`services/billing.py`); falls back to sandbox mock when credentials are omitted |
| WhatsApp Business API / SMTP notifications | In-app notifications are real; email/WhatsApp just log what would be sent (`services/notify.py`) |
| Voice interview simulator | Text-based panel round (voice is explicitly a §12 Phase-4 extension) |
| Native mobile app | Web only |

Swapping any mock for the real thing is a localized change in one `services/*.py`
file — none of the API surface or frontend needs to change when that happens.

## Phase-by-phase status (§12)

- **Phase 0 — Foundation:** auth (JWT, 4 roles), the full syllabus graph,
  and a public marketing/lead-gen site (`/`) are all built.
- **Phase 1 — Core Prep Loop:** Prelims mock-test engine (real −⅓ negative
  marking), current-affairs digest (MOD-03, AI-tagged to syllabus nodes),
  and the SM-2 revision scheduler (MOD-06) are all built.
- **Phase 2 — Mains AI Evaluation:** the rubric grading engine, a typed
  *and* photographed-scan answer workspace, and the async grading queue
  are all built.
- **Phase 3 — Interview & Mentorship:** DAF intake, the text-based panel
  simulator (MOD-08), conceptual doubt-resolution with citations (MOD-07),
  and the mentor QA/override console (MOD-09) are all built.
- **Phase 4 — Scale & Intelligence:** out of scope by design (ongoing,
  post-launch) except for a first-cut Prelims percentile estimate in
  `analytics.py`. AIR prediction proper, voice interview, and a mobile app
  are still future work.

## Structure

```
backend/    FastAPI + Motor (MongoDB) — app/api/v1 has one router per module
            app/data/ has the real seed content (see below)
frontend/   Next.js + TypeScript + Tailwind — one page per module under app/
docs/       drop the architecture doc/export here for reference
```

## Content: what's actually seeded

`backend/app/data/subjects/*.json` holds one file per GS paper, CSAT, Essay,
and each of the 25 UPSC Optional subjects — real official-syllabus topic
trees, real past UPSC PYQs (descriptive + MCQ), and platform-authored (never
copy-pasted) reading-material summaries. `backend/app/data/current_affairs.json`
holds a current-affairs digest batch, auto-tagged to syllabus nodes via the
AI classification pipeline at seed time. As seeded: **823 syllabus nodes,
440 PYQs, 422 content items** across all 6 core papers and all 25 Optionals,
plus 27 current-affairs entries. Schema is documented in
`backend/app/data/SCHEMA.md` — extend any subject by adding to its file and
re-running the seeder (it's idempotent, matched by natural key).

## Before you run anything

This machine's C: drive runs chronically low on space — redirect npm/pip
caches to D: before installing if you haven't already:

```powershell
npm config set cache "D:\npm-cache" --global
pip config set global.cache-dir "D:\pip-cache"
```

## Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m app.seed          # 4 demo users + a small hand-written GS2/GS3/CSAT slice
python -m app.seed_content  # the real syllabus/PYQ/content library — run this too
uvicorn app.main:app --reload --port 8000
```

While `uvicorn` is running, it refreshes the current-affairs digest with real
headlines once at startup and then every 24h on its own — no extra step
needed. To force a refresh without waiting (e.g. to see it work right away),
either run `python -m app.ingest_current_affairs` in a second terminal, or
hit `POST /api/v1/content/current-affairs/refresh` as a content_editor/admin.
Set `NEWS_INGEST_ENABLED=false` in `.env` to turn the automatic refresh off.

**`.env` already exists with real values filled in** — `MONGODB_URI`,
`ANTHROPIC_API_KEY`, and a real `JWT_SECRET`. **Do NOT run
`copy .env.example .env`** if you're re-following these steps on this same
checkout — it overwrites the real file with `.env.example`'s placeholders
and every command above then fails with a DNS/`<cluster>.mongodb.net`
error. `.env.example` is only a template for a *fresh* clone that has no
`.env` yet.

Demo accounts (password `Nirdesh@2026`): `aspirant@demo.com`,
`mentor@demo.com`, `editor@demo.com`, `admin@demo.com`.

## Frontend

```bash
cd frontend
npm install
copy .env.local.example .env.local
npm run dev      # http://localhost:3000
```

Log in, then the nav bar has every module: Dashboard, Syllabus, Mains
Practice, Prelims Mock, Revision, Current Affairs, Doubts, Interview,
Billing — plus a Mentor Queue link for the mentor account and a Content CMS
link for the editor/admin accounts.

**Cost note:** `grading_model` in `backend/app/core/config.py` defaults to
`claude-opus-5` for grading/interview quality. §08 flags Sonnet-class
routing as the cost lever once you're grading at volume — it's a one-line
change in that file.

## What's still genuinely open

- **Live external accounts** — see the mock-vs-real table above. Each is a
  contained swap when you're ready for a real Razorpay/WhatsApp/OCR vendor.
- **Redis-backed queue** — `BackgroundTasks` works for a prototype's load;
  move `services/grading.py`'s call site to a real queue (Redis + RQ/Celery)
  once you're grading more than a handful of answers concurrently.
- **Literature optional subjects** — the 25 non-literature Optionals are
  seeded; UPSC's separate language-literature list isn't.
- **Phase 4 proper** — AIR-rank prediction beyond the current rough
  percentile-vs-cutoff estimate, voice interview articulation, and a native
  mobile app are intentionally not attempted here.
