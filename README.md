# Voice-to-Order

A locally runnable, **public and fully anonymized** replica of a voice-ordering system that
runs in production for a real industrial plumbing/HVAC supplier. A field technician dictates an
order; the system transcribes it, extracts the lines with an LLM, matches each line against a
**~31,000-row catalog and a learned memory** (pgvector / HNSW vector search + re-ranking), a
human reviews and corrects, and the order is delivered over three independent channels.

It runs with **Docker + two commands**, on **real anonymized data**, with **no cloud
dependencies**. Built as the runnable companion to case study 06 of the *LLM context systems*
portfolio (published separately).

> ⚠️ **Local-only by design.** There is no authentication (it binds to `127.0.0.1`). Do not
> expose it to a network without adding auth and rate limiting — real mode spends real API
> quota. See the security note below.

---

## Two modes

| | **Demo** (default, no API keys) | **Real** (your own `.env`) |
|---|---|---|
| Transcription | replays 47 real recorded orders (anonymized) | live `whisper-1` |
| Extraction | replays the validated order lines | live `gemini-2.5-flash` |
| Vector search | **real**, against the local Postgres+pgvector with committed embeddings | live query embeddings |
| Re-ranking | the deterministic fallback (original production behavior) | live `gemini-2.5-flash` |
| Delivery (PDF / ERP / email) | simulated channels, real PDF | simulated channels, real PDF |

Demo mode reproduces the full 7-step flow end to end **with no keys and no network** — the
vector search is genuinely running against the real (anonymized) corpus.

---

## Quickstart (demo mode, 2 commands)

Requirements: Docker, Python 3.12+, Node 20+ (only for the UI).

```bash
# 1. Local Postgres + pgvector (schema + functions auto-applied on first boot)
docker-compose -f db/docker-compose.yml up -d

# 2. Load the anonymized dataset + committed embeddings into the DB
python tools/load_database.py
```

Then start the backend and (optionally) the UI:

```bash
python serve.py                 # API on http://127.0.0.1:8000
                                # (use `python serve.py 8010` if 8000 is taken)

cd src/frontend && npm install && npm run dev   # UI on http://localhost:5173
```

Open the UI, pick one of the 47 recorded orders, and click through:
**process → review candidates → finalize → send** (with three status lights). The UI chrome
is bilingual — an `ES|EN` toggle in the header, detected from the browser and remembered —
while the dataset text (transcriptions, catalog descriptions) stays Spanish and verbatim.

> On Windows, start the backend with `python serve.py`, **not** `uvicorn ...` directly:
> psycopg's async pool needs a selector event loop, which `serve.py` sets up.

A step-by-step walkthrough of the five screens, written for someone using the app rather than
reading its code, is in [docs/USER_GUIDE.md](docs/USER_GUIDE.md).

### Real mode

Copy `.env.example` to `.env`, set `APP_MODE=real` and your `OPENAI_API_KEY` /
`GOOGLE_API_KEY`, and restart. The opt-in live test is:

```bash
RUN_REAL_MODE_TESTS=1 pytest tests/realmode -v   # spends API quota; skipped by default
```

Approximate cost: **≈ US$0.01 per order**, Whisper-dominated (see
[docs/plans/phase_6/6.1_real_run_evidence.md](docs/plans/phase_6/6.1_real_run_evidence.md)).

---

## What is real vs synthetic

- **Real, anonymized** — the catalog (31,069 rows), the learned memory (974 mappings) and the
  47 validated transcription→order pairs are real operational data, published only after an
  irreversible, verifiable anonymization process. Article ids are HMAC-SHA256 tokens; customer/
  site/order-ref/phone/person/supplier names are tokenized; dates are reduced to month. The
  dictated text and catalog descriptions are kept **verbatim** (Spanish) — they *are* the
  matching problem this project demonstrates. Details: [data/README.md](data/README.md),
  [docs/refs/legal-framework-anonymization.md](docs/refs/legal-framework-anonymization.md).
- **No audio is published** — voice is biometric data. Demo "audio" is replayed text; the
  real-mode E2E uses synthetic text-to-speech, never committed.
- **Simulated** — the ERP and email delivery channels (the production system talks to a real
  ERP and Office 365; here they write artifacts to `.tmp/` and expose the same status-light
  contract + a `SIMULATE_FAILURE` chaos switch). The PDF is real.
- **No real client, customer, site or part number** appears anywhere in the code, data, docs
  or git history.

---

## Architecture (one paragraph)

FastAPI, async end to end. The signature design — ported verbatim from production — is the
per-article search: one `asyncio` task per order line, fanned out with `asyncio.gather` and
bounded by **two named semaphores** (LLM=10, DB=10); each line searches the **learned memory
first** (threshold 0.75) then the **catalog** (threshold 0.5, top 25), then an LLM re-rank that
**degrades to a deterministic sort** rather than erroring. The pgvector lookups use CTE/HNSW SQL
functions ported verbatim (the `ORDER BY embedding <=> q LIMIT n*3` pattern that actually
triggers the index scan). Delivery runs three independent channels, each with its own status
light, so one failing never aborts the others; every confirmed line feeds back into the memory
so next month's search is better than this month's.

```
React (Vite, multi-step) --> FastAPI --+- transcription   (demo replay | whisper-1)
                                       +- extraction      (demo replay | gemini-2.5-flash, retry x3)
                                       +- search          asyncio.gather + 2 semaphores
                                       |     +- Postgres+pgvector: buscar_historicos / buscar_articulos
                                       +- delivery        PDF + simulated ERP + simulated email
                                       +- learning loop   upsert confirmed line -> memory
```

Full design: [docs/plans/](docs/plans/) and the case study.

---

## Tests

```bash
pytest                                       # 128 passed, 1 skipped (real-mode opt-in)
python tools/verify_anonymization.py         # anonymization gate over data/ (structural)
python tools/history_sweep.py --terms <file> # real-terms sweep over the WHOLE git history
```

The last one takes the real-terms list, which is deliberately not in this repo — it is the
author's pre-publication gate, and it reports *where* a term appears without ever printing
it. `data/`-touching changes run the first two; a publication runs all three.

DB-backed tests skip cleanly when the database is not up, so the suite stays green without
Docker. CI runs the suite + the anonymization gate + a dependency scan on every push
([.github/workflows/ci.yml](.github/workflows/ci.yml)).

---

## Security posture

No critical/high findings in the release-gate audit
([docs/security/audit-2026-06-17-full.md](docs/security/audit-2026-06-17-full.md)). The app is
intentionally local-only and unauthenticated; that is the documented threat model, mitigated by
the `127.0.0.1` binding. Audio uploads are capped (25 MB) and type-checked; SQL is
parameterized; no secrets are committed.

---

## Project layout

```
src/backend/    FastAPI app (routers, services, core)   src/frontend/  React SPA
db/             docker-compose + schema + CTE/HNSW SQL   data/          anonymized dataset + embeddings
tools/          anonymization, DB load, embeddings       tests/         pytest (backend, db, tools)
docs/plans/     spec-driven phase docs                   docs/security/ audit reports
```

Built with a spec-driven workflow (SDD): every phase has a spec, a plan and tests. See
[docs/plans/0_master_plan.md](docs/plans/0_master_plan.md).

---

## License

Code: [MIT](LICENSE). Dataset in `data/`: CC BY-NC 4.0, for evaluation and research, with
re-identification expressly disallowed — see [LICENSE](LICENSE) for both.
