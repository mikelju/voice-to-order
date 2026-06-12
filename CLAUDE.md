# CLAUDE.md — Voice-to-Order (public local replica)

Project rules and context for the agent. Always read before making changes.

> **SDD-WAT framework:** this project uses the framework documented in `CLAUDE_GLOBAL.md` (root).
> This CLAUDE.md defines what is project-specific. It is a seed version written at project start;
> `/3-init-project` will regenerate/enrich it as the code grows.

---

## What is this project?

A **public, locally runnable** replica of the voice-ordering system in production for a real client:
dictated audio → transcription → LLM extraction → per-article vector search (~31k catalog + learned
memory, pgvector/HNSW) → human review → multi-channel delivery. No cloud dependencies (local Docker +
Postgres+pgvector), **real anonymized data**, two modes: **demo** (no API keys; recorded replays +
real vector search) and **real** (live Whisper/Gemini with the user's own `.env`). Status: starting —
see `docs/plans/0_master_plan.md`.

**Audience:** recruiters/technical reviewers. The repo will be **public**: every content decision is
made assuming anyone will read it. The repo language is **English** (the dataset's dictated text and
article descriptions are Spanish by nature — kept verbatim as evidence).

---

## Development commands

```bash
docker-compose -f db/docker-compose.yml up -d # Local Postgres+pgvector (port 5433)
python tools/load_database.py                 # Load data/ into the DB
python tools/apply_sql.py                     # Re-apply functions/phase SQL to a live DB
python serve.py                               # Backend dev server, port 8000 (8010 if busy)
                                              #   (NOT plain `uvicorn ...`: psycopg async
                                              #    needs a selector loop on Windows)
npm run dev                                   # Frontend (src/frontend) — Phase 5
pytest                                        # Tests (DB tests skip if the DB is down)
python tools/verify_anonymization.py          # Anonymization gate over data/
```

---

## Architecture

### File structure

```
src/
├── backend/        # FastAPI: routers, services (transcription/extraction/search/delivery), core
└── frontend/       # React (Vite+TS+Tailwind): multi-step flow
tools/              # WAT: anonymization, verification, DB load, embeddings (deterministic)
workflows/          # WAT: SOPs for the repeatable processes (anonymize, load, publish)
data/               # ONLY versioned anonymized data (catalog, history, extraction pairs)
db/                 # docker-compose + schema SQL and functions (CTE/HNSW ported from the original)
tests/              # mirrors src/ and tools/
docs/plans/         # SDD: master plan, phases, fixes
docs/security/      # /8-audit reports
docs/refs/          # legal framework for the anonymization
```

### Main pattern

The original system's (validated in production; ported, not redesigned):
**router → service → DB**, async end-to-end; per-article parallel search with `asyncio.gather`
bounded by **two named semaphores** (LLM=10, DB=10); memory-first (threshold 0.75) → catalog
(0.5, top 25) → re-rank with a **deterministic fallback**; delivery over 3 independent channels with
status lights and the `SIMULATE_FAILURE` chaos switch.

### Demo mode vs real mode

A single variable (`APP_MODE=demo|real`). In demo, transcription/extraction/re-rank are served from
**recorded replays** (real anonymized pairs) and vector search is **real** against the local DB with
precomputed embeddings. In real mode, everything live. Provider selection is by model-name prefix
(wrapper ported from the original).

---

## Tech stack

| Layer | Technology | Notes |
|------|-----------|-------|
| Backend | Python 3.12+ / FastAPI | async end-to-end |
| DB | PostgreSQL 16 + pgvector (HNSW) | Docker, `docker-compose.yml` |
| Frontend | React + Vite + TypeScript + Tailwind | port of the original, no client branding |
| Models (real mode) | whisper-1 · gemini-2.5-flash · text-embedding-3-small | user keys via `.env` |
| Tests | pytest (backend/tools) | test-first per the framework |

---

## Environment variables

```env
APP_MODE=demo                # demo | real
DATABASE_URL=                # Local Postgres (docker-compose)
OPENAI_API_KEY=              # real mode / embeddings generation only
GOOGLE_API_KEY=              # real mode only
SIMULATE_FAILURE=            # chaos: erp,email,history
# Anonymization tool only (author's machine, NEVER in the repo):
REAL_DATA_DIR=               # path to the real data
ANON_SALT=                   # secret salt for the id HMAC
REAL_REPLACEMENTS_FILE=      # term=>token mapping of real names
```

---

## Code conventions

- Python: per `CLAUDE_GLOBAL.md` (no special Unicode in code output: `[OK]`, `->`).
- Async services; no blocking calls on the event loop (original's lesson: a *half*-async stack =
  socket exhaustion).
- The meaningful values from the original (semaphores 10/10, thresholds 0.75/0.5, top-25, CTE ×3,
  retry ×3 backoff 2s·attempt) are kept and named as constants — they are part of what this repo
  demonstrates.
- Mirrored tests in `tests/`; every spec acceptance criterion has a test.

---

## Agent permissions

✅ **ALWAYS** (do without asking):
- Run `tools/verify_anonymization.py` after any change to `data/`
- Run tests before marking tasks `[x]`
- Follow the SDD flow (spec → plan → implement → verify)

⚠️ **ASK FIRST**:
- Anything that spends paid API quota (embeddings, real mode)
- Adding new dependencies
- Publishing/pushing to the public remote
- Touching the real source data (read-only; never copied into the repo without anonymization)

🚫 **NEVER** (no exceptions):
- Commit unanonymized real data, real audio (biometrics), secrets or `.env`
- Include real names of the client, its customers, sites, suppliers or real part numbers — not in
  code, docs or commit messages (the git history will be public)
- Run anything against the original system's production infrastructure
- Weaken the anonymization verification to make it pass

---

## Project anti-patterns

🚫 Inventing "example" data mixed with the anonymized real data — either it is real-anonymized and
   declared, or synthetic and labeled; never ambiguous.
🚫 Complex logic inline in routers — always a service.
🚫 `asyncio.to_thread` over clients that have an async version — true async end-to-end.
🚫 "Improving" the ported CTE SQL functions — they are ported verbatim from the original (they are
   evidence); any change is documented as a deviation.

---

## Known gotchas

1. **The git history will be public**: a real term committed and later deleted remains in history.
   The anonymization sweep runs **before** every commit touching `data/` or docs.
2. The real-terms list and the hash salt live **outside the repo**
   (`C:\Python Projects\portfolio-private\`): without the salt, `ART-…` ids are not reversible.
3. Windows + consoles: the original suffered `charmap` crashes — all print/log output ASCII-safe.
4. pgvector only uses the HNSW index with the `ORDER BY embedding <=> q LIMIT n` pattern (the reason
   the ported CTE functions exist — do not "simplify" them).

---

## Evolution plan

The full roadmap is in `docs/plans/0_master_plan.md` (7 phases).

**Before any change:**
- New phase → `/4-specify` → `/5-plan` → `/6-implement` → `/7-verify` → `/8-audit` → `/9-document`
- Bug fix → `/5-plan` (if non-trivial) → `/6-implement` → `/7-verify`
- Before the first public push → full `/8-audit` + anonymization verification with the complete
  terms list + git-history sweep

> Method note (agreed with the author): the original system is already in production, so specs are
> **derived** from it rather than discovered; the framework is followed for traceability, not to the
> letter in the bootstrap commands.

Invoke `/prime` at the start of each session to load context.

---

## Security audit

The `/8-audit` command (`audit-code` skill) is mandatory before the release gate (Phase 7) and when
closing phases that touch external input (audio upload, real mode). Reports in `docs/security/`.
See `CLAUDE_GLOBAL.md` → "Security audit".
