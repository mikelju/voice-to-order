# Master Plan: Voice-to-Order (public local replica)

## What is this product?

A **locally runnable** replica of a voice-ordering system that is in production for a real client (an
industrial plumbing/HVAC supplier): a technician dictates an order, the system transcribes it,
extracts the lines with an LLM, matches each article against a ~31,000-row catalog and a learned
history (pgvector/HNSW vector search + re-ranking), a human reviews, and the order is delivered over
three channels. This replica removes the original's cloud dependencies (Google Cloud Run, Supabase
Cloud, the client's ERP) and uses **real, anonymized data**; it runs with Docker + two commands.

**For whom:** recruiters and technical reviewers who want to run and read the system described in
[case study 06 of the portfolio](https://github.com/mikelju/llm-context-systems-portfolio); and as a
Biar Tech demonstration base.

**Two modes:**
- **Demo mode (default, no API keys):** transcription and extraction replay real recorded pairs
  (anonymized); vector search runs for real against Postgres+pgvector with precomputed embeddings
  shipped in the repo.
- **Real mode (own `.env`):** Whisper (transcription), Gemini (extraction + re-ranking) and live
  embeddings.

**What it is NOT (anti-goals):** not the production system (no multi-user auth, no real ERP — a
simulated channel, no nightly sync); it publishes no real audio (voices are biometric data — see
`docs/refs/legal-framework-anonymization.md`); it contains no real identifier of the client, of the
client's customers, or real part numbers.

## Reference: the original system

The design replicates the production project (private). The architecture decisions are already made
and validated there; this plan does not rediscover them, it **ports** them:

| Original decision | Ported as |
|---|---|
| FastAPI async end-to-end, one service per stage | same, `src/backend/` |
| Per-article parallel search: `asyncio.gather` + LLM/DB semaphores (10/10) | same |
| Learned-memory first (threshold 0.75, count 1) → catalog (0.5, top 25) → re-rank with deterministic fallback | same |
| CTE SQL functions forcing the HNSW index scan (`ORDER BY <=> LIMIT n*3`) + `SET statement_timeout` | same (SQL ported verbatim, anonymized) |
| Extraction retry ×3 with 2s·attempt backoff | same |
| 3 independent delivery channels with status lights + `SIMULATE_FAILURE` chaos switch | ERP and email become **simulated channels**; PDF real |
| React multi-step (table with per-row dropdowns) | same, `src/frontend/`, without client branding |
| Supabase Cloud (pgvector, auth) | **Postgres+pgvector in Docker** (docker-compose); no auth |

## Documentation convention

Every modification, improvement or fix follows this protocol before touching code:

```
docs/plans/
├── 0_master_plan.md           # This file — global vision
├── phase_1/
│   ├── 1.spec.md              # Functional specification (WHAT + WHY) — /4-specify
│   ├── 1.0_phase_name.md      # Implementation plan (HOW) — /5-plan
│   └── 1.Y_name.md            # Deviation/issue (Y = 1, 2, 3…)
├── phase_2/
│   └── ...
└── fixes/
    └── fix-N_name.md          # One-off bug fix (globally sequential)
```

**Per-phase workflow:** `/4-specify` → `/5-plan` → `/6-implement` → `/7-verify`

> Method note: since the original system already exists and is validated in production, this
> project's specs are **derived** from it (there is no discovery phase). The framework is followed
> for traceability and reviewability, not to rediscover decisions already made.

---

## Phase status

| Phase | Name | Spec | Status |
|------|--------|------|--------|
| 1 | Anonymized dataset + verification | Done | Done |
| 2 | Local database (Postgres+pgvector, schema, CTE functions) | Done | Done |
| 3 | FastAPI backend (full pipeline in demo mode) | Done | Done¹ |
| 4 | Precomputed embeddings (needs an API key — decision pending) | Done | Done¹ |
| 5 | React frontend | Done | Done¹ |
| 6 | Real mode (live Whisper + Gemini) + E2E | Done | Done |
| 7 | Security audit + public README + release gate | Done | In progress² |

---

## Phase 1: Anonymized dataset + verification

**Goal:** the real data (catalog ~31k rows, ~1k learned mappings, validated extraction pairs) enters
the repo **only** in anonymized form, with automated, repeatable verification.

- [x] `tools/anonymize_dataset.py` — reads the real data (paths and secret salt via env vars, outside
      the repo), applies the anonymization scheme (salted-HMAC ids, `[customer]`/`[site]`/
      `[order-ref]`/`[phone]`, dropped columns, dates → month) and writes `data/`
- [x] `tools/verify_anonymization.py` — gate anyone can run over `data/` (structural patterns +
      secrets + phones); `--terms` mode with the real list kept outside the repo
- [x] Manual-review report of unlisted proper nouns (for the author's review)
- [x] Tests for both tools; `data/` versioned and green

## Phase 2: Local database

**Goal:** `docker-compose up` brings up Postgres+pgvector with the ported real schema.

- [x] `docker-compose.yml` (pgvector image) + init SQL: `catalogo`, `embeddings`, `historico` tables
- [x] CTE functions ported from the original: `buscar_articulos`, `buscar_historicos`
      (`ORDER BY <=> LIMIT n*3` pattern, `SET statement_timeout`), HNSW index
- [x] `tools/load_database.py` — loads `data/` into the DB
- [x] Integration tests against the local DB

¹ Phase-3 security audit explicitly deferred to the Phase-7 `/8-audit full` release gate
(single audit covers backend+frontend+tools before the public push; decision recorded here).

## Phase 3: FastAPI backend (full demo mode)

**Goal:** the 7-step flow runs end-to-end locally with no API keys.

- [x] Ported services: transcription (demo: replay), extraction (demo: replay of recorded pairs),
      search (real against the DB: gather + semaphores + fallback), delivery (real PDF + simulated
      ERP/email with status lights + `SIMULATE_FAILURE`)
- [x] Endpoints: process-audio / search-articles / finalize / send (+ GET /demo/recordings)
- [x] Learned memory: history upsert on confirmation (both modes — documented deviation)
- [x] Per-service tests + flow test (106 tests; E2E demo + chaos run)

## Phase 4: Precomputed embeddings

**Goal:** demo-mode vector search uses real committed embeddings.

- [ ] API-key decision with the author (pending)
- [ ] `tools/generate_embeddings.py` (one-off run; reduced dimension to keep the repo small)
- [ ] Versioned vectors + DB load + basic recall verification against the history

## Phase 5: React frontend

**Goal:** the real multi-step UI, without client branding.

- [ ] Frontend port (Vite+TS+Tailwind): upload/dictate → review extraction → candidate table with
      per-row dropdowns → finalize → delivery status lights
- [ ] Biar Tech branding
- [ ] Build and test against the local backend

## Phase 6: Real mode + E2E

**Goal:** with the user's own `.env`, the pipeline uses live models.

- [x] Ported multi-provider LLM wrapper; mode flags
- [x] Live Whisper + Gemini; live query embeddings (executed E2E — `phase_6/6.1`)
- [x] E2E: demo mode (CI-able, 116 tests) + real mode (opt-in `tests/realmode/`, manual)
- [x] Document approximate per-query costs (`phase_6/6.1`: ~US$0.01/order, Whisper-dominated)

## Phase 7: Audit + release gate

**Goal:** public repo ready for recruiters.

- [x] Full `/8-audit` (release gate) + `docs/security/audit-2026-06-17-full.md`
      (0 Critical, 0 High; Medium/Low hardening applied — SEC-001..004)
- [x] Recruiter-oriented public README (2-command quickstart, what is real, link to case study 06)
- [ ] Final anonymization verification (`--terms`) + git-history sweep before the first push
      (OBS-001 — author machine, external terms list; **still pending — publish blocker**)
- [x] Basic CI (`.github/workflows/ci.yml`: tests + anonymization gate + pip-audit + frontend build)

² Phase 7 code work is complete and the suite is green; the phase closes (and the first public
push happens) only after the pre-push anonymization sweep (`--terms` + git history) passes.

---

## Fixes

_(No fixes recorded — project starting up)_
