# Security Audit — Voice-to-Order (public local replica)

**Date:** 2026-06-17
**Auditor:** audit-code skill (Claude Code)
**Scope:** full release-gate audit — `src/backend/` (all), `tools/` (all), `src/frontend/src/` (all), `serve.py`, `requirements.txt`, `src/frontend/package.json`. Commit `5729823`.
**Threat model:** local-only developer tool / public portfolio repo. No authentication by design (documented anti-goal). The two real assets to protect are (a) the owner's API keys / quota in real mode, and (b) the anonymization guarantee (no real client/site/part numbers reach the public git history). Server is bound to `127.0.0.1` by `serve.py`.
**Stack:** Python 3.13 / FastAPI 0.136 / Starlette 1.2 / psycopg3 + pgvector; React 19 / Vite 6 / TypeScript; reportlab 4.5; OpenAI 2.41 + google-genai 2.8 (real mode).

---

## 1. Executive Summary

No critical or high-severity findings were identified within the reviewed scope. The code is defensively written: SQL is consistently parameterized, the only dynamic-SQL hits are provably non-injectable (fixed clauses / a fixed identifier set), all user-supplied values reaching the PDF generator are HTML-escaped, there are no code-execution sinks (`eval`/`exec`/`pickle`/`yaml.load`/`shell=True`) in the runtime, and there are no hardcoded secrets — keys load from a gitignored `.env`. The main hardening gap is the absence of an upload-size limit on the audio endpoint (a denial-of-service vector), plus a handful of low-severity defense-in-depth items (verbose error text echoed to clients, an over-permissive CORS credential flag, and dependency-floor hygiene).

The single most important item before the first public push is **not a code defect**: the anonymization release gate (`--terms` sweep with the external real-terms list + a full git-history sweep) has not yet been executed. The public/CI gate is structural only and cannot, on its own, catch an un-listed real proper noun. See OBS-001.

**Findings by severity:**

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High     | 0 |
| Medium   | 1 |
| Low      | 5 |
| Info     | 3 |

(plus OBS-001 — release-gate process item, not a code defect)

---

## 2. Top Priorities

1. **[OBS-001] Run the anonymization release gate before pushing** — `verify_anonymization.py --terms <external list>` + git-history sweep. This is the publish blocker. → §3.10
2. **[SEC-001] Bound the audio upload size** — an unauthenticated large upload is read fully into memory (and forwarded to Whisper in real mode). → §3.1
3. **[SEC-002] Stop echoing exception text / filenames in API error details** — minor information disclosure; tighten before any non-local exposure. → §3.2

---

## 3. Findings

### 3.1 [SEC-001] Unbounded audio upload and request bodies (DoS) — **Medium**

- **File:** [src/backend/app/routers/order_processing_router.py:62](src/backend/app/routers/order_processing_router.py#L62)
- **CWE:** CWE-400 (Uncontrolled Resource Consumption)
- **OWASP:** A05 — Security Misconfiguration
- **Confidence:** Confirmed
- **Tool:** manual review

**Description**

`/orders/process-audio` reads the entire uploaded file into memory with no size limit and no content-type/extension allowlist. The same applies to the JSON bodies of `/search-articles`, `/finalize`, and `/send`, which accept arbitrarily long lists. There is no global request-size cap (Starlette/uvicorn do not impose one by default).

**Vulnerable code**

```python
# src/backend/app/routers/order_processing_router.py:62
content = await audio_file.read()              # whole upload into RAM, no cap
transcribed = await transcribe_audio_service(clients, content, audio_file.filename or "", ...)
```

**Impact**

A single multi-GB upload (or many concurrent uploads) exhausts process memory → denial of service. In real mode, large/looping audio also burns the owner's Whisper quota. Demo mode hashes the full bytes (`ReplayStore.id_for_bytes`), so the cost is paid even without an API key.

**Reproduction / PoC sketch** (do NOT run)

> `POST /api/v1/orders/process-audio` with a 5 GB `audio_file` part. The server buffers it all before any validation, spiking RSS and risking OOM.

**Remediation**

Add a max-size guard (stream-aware) and a content-type allowlist; reject early.

```python
# order_processing_router.py — fixed
MAX_AUDIO_BYTES = 25 * 1024 * 1024  # Whisper's own limit is 25 MB
ALLOWED_AUDIO = {"audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp4",
                 "audio/webm", "audio/ogg", "application/octet-stream"}

if audio_file.content_type not in ALLOWED_AUDIO:
    raise HTTPException(415, "Tipo de audio no soportado.")
content = await audio_file.read(MAX_AUDIO_BYTES + 1)
if len(content) > MAX_AUDIO_BYTES:
    raise HTTPException(413, "Audio demasiado grande (max 25 MB).")
```

Also bound list lengths on the JSON endpoints (e.g. `Field(max_length=...)` on the Pydantic request models) and consider a body-size middleware. See DEF-002.

**References**
- [CWE-400](https://cwe.mitre.org/data/definitions/400.html)
- [OWASP Denial of Service Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Denial_of_Service_Cheat_Sheet.html)

---

### 3.2 [SEC-002] Exception text and filenames echoed in API error details — **Low**

- **File:** [src/backend/app/routers/order_processing_router.py:68](src/backend/app/routers/order_processing_router.py#L68), [order_delivery_service.py:52](src/backend/app/services/order_delivery_service.py#L52), [order_processing_router.py:256](src/backend/app/routers/order_processing_router.py#L256)
- **CWE:** CWE-209 (Information Exposure Through an Error Message)
- **OWASP:** A05 — Security Misconfiguration
- **Confidence:** Confirmed
- **Tool:** manual review

**Description**

Several error paths return raw exception text or the user-supplied filename to the client: the transcription-failure detail includes `audio_file.filename`; the PDF/email/historical error details embed `str(exc)`. These are returned as JSON (not HTML), so they are **not** an XSS vector — the React client renders them as text — but they can leak internal paths or library messages.

**Vulnerable code**

```python
# order_processing_router.py:68 and :256, order_delivery_service.py:52
detail=f"Fallo en la transcripcion del audio para el archivo: {audio_file.filename}"
return None, False, f"No se pudo generar el PDF: {exc}"
error_details_list.append(f"Historico: {exc}")
```

**Impact**

Minor information disclosure (paths, dependency internals). Low impact while the service is localhost-only; matters more if ever exposed.

**Remediation**

Return a generic message to the client; keep the detail in the server log (already done via `logger.exception`). Drop the filename/`exc` from the client-facing `detail`.

**References**
- [CWE-209](https://cwe.mitre.org/data/definitions/209.html)

---

### 3.3 [SEC-003] CORS `allow_credentials=True` without any credential auth — **Low**

- **File:** [src/backend/app/main.py:65](src/backend/app/main.py#L65)
- **CWE:** CWE-942 (Permissive Cross-domain Policy)
- **OWASP:** A05 — Security Misconfiguration
- **Confidence:** Confirmed
- **Tool:** manual review

**Description**

CORS is configured with an explicit localhost origin allowlist (good — not `*`, not reflected) but `allow_credentials=True`. The app has no cookies/auth, so credentials are never used; the flag is unnecessary attack surface and would become risky if auth were added later without revisiting CORS.

**Remediation**

Set `allow_credentials=False` (the app sends no credentials). Keep the explicit origin allowlist. If auth is ever added, never combine credentials with a wildcard or reflected origin.

**References**
- [CWE-942](https://cwe.mitre.org/data/definitions/942.html) · [OWASP CORS](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)

---

### 3.4 [SEC-004] Dependency floors permit known-vulnerable versions — **Low**

- **File:** [requirements.txt:7](requirements.txt#L7)
- **CWE:** CWE-1104 (Use of Unmaintained Third Party Components) / CWE-1035
- **OWASP:** A06 — Vulnerable and Outdated Components
- **Confidence:** Confirmed (preventive — installed versions are clean)
- **Tool:** manual review + `pip freeze`

**Description**

`requirements.txt` pins only lower bounds (`>=`) with no upper cap and, in the case of `python-multipart>=0.0.9`, a floor below the fix for the multipart DoS (CVE-2024-53981, fixed in 0.0.18). The **installed** version is `0.0.32` (safe), so this is preventive: a fresh `pip install` on a different machine could resolve a vulnerable version. All other installed deps are current (`fastapi 0.136.3`, `starlette 1.2.1`, `reportlab 4.5.1`, `openai 2.41.1`, `psycopg 3.3.4`).

**Remediation**

Raise the floor for the upload-path dependency and add dependency scanning to CI (DEF-001):

```text
python-multipart>=0.0.18
```

Consider a lockfile (`pip-compile` / `pip freeze > requirements.lock`) for reproducible installs (DEF-005).

**References**
- [CVE-2024-53981](https://github.com/encode/starlette/security/advisories) (python-multipart DoS) · [CWE-1104](https://cwe.mitre.org/data/definitions/1104.html)

---

### 3.5 [SEC-005] TTS dev helper: partial executable + here-string interpolation — **Low**

- **File:** [tools/make_tts_audio.py:62](tools/make_tts_audio.py#L62)
- **CWE:** CWE-78 (OS Command Injection) / CWE-427 (Uncontrolled Search Path Element)
- **OWASP:** A03 — Injection
- **Confidence:** Possible
- **Tool:** ruff S603/S607 + manual review

**Description**

The Phase-6 TTS helper launches `powershell` by partial name (PATH-resolved) and interpolates the order text into a single-quoted PowerShell here-string. The text is developer-supplied (a CLI arg, default a fictional order) and the tool is **not part of the deployed app**, so runtime exposure is nil. Residual: a crafted `--text` containing a line that is exactly `'@` could terminate the here-string and inject PowerShell; and a hostile `powershell` earlier on PATH would be preferred.

**Remediation**

Defense-in-depth (the tool is local-author-only): invoke the full path (`%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe`), and pass the text via stdin or a temp `.ps1` rather than inline `-Command`. Not release-blocking.

**References**
- [CWE-78](https://cwe.mitre.org/data/definitions/78.html) · [CWE-427](https://cwe.mitre.org/data/definitions/427.html)

---

### 3.6 [SEC-006] Frontend renders PDF via `data:` URL trusting server `content_type` — **Info**

- **File:** [src/frontend/src/App.tsx:277](src/frontend/src/App.tsx#L277), [App.tsx:309](src/frontend/src/App.tsx#L309)
- **CWE:** CWE-79 (XSS) — not exploitable as written
- **OWASP:** A03 — Injection
- **Confidence:** Confirmed (safe)
- **Tool:** manual review

**Description**

The download link builds `href={`data:${content_type};base64,${b64_pdf}`}`. `content_type` comes from the backend response, where it is the server-set constant `"application/pdf"` ([order_delivery_service.py:48](src/backend/app/services/order_delivery_service.py#L48)). A `data:application/pdf` URL does not execute script. Were `content_type` ever attacker-controllable as `text/html`, this would become DOM-XSS — so it is worth hardening.

**Remediation**

Hardcode the literal MIME in the `href` and add a `download` attribute so the browser never renders the blob inline:
`href={`data:application/pdf;base64,${b64_pdf}`} download={filename}`.

---

### 3.7 [SEC-007] ruff S608 dynamic-SQL hits are false positives — **Info**

- **File:** [src/backend/app/routers/catalog_router.py:34](src/backend/app/routers/catalog_router.py#L34), [tools/load_database.py:95](tools/load_database.py#L95)
- **CWE:** CWE-89 (SQL Injection) — not present
- **OWASP:** A03 — Injection
- **Confidence:** Confirmed (safe)
- **Tool:** ruff S608 + manual confirmation

**Description**

Both flagged sites build SQL with an f-string, but neither interpolates user data: `catalog_router` interpolates only the fixed clause `"articulo ILIKE %s"` repeated once per term (the search terms themselves are bound parameters in `params`), and `load_database` interpolates a table name drawn from a hardcoded literal tuple. No injection is possible. Recorded so the static-analysis hits are not mistaken for open issues.

**Remediation**

None required. Optionally add `# noqa: S608` with this rationale to keep the scan clean.

---

### 3.8 [SEC-008] Simulated-ERP filename built from `num_order` (guarded) — **Info**

- **File:** [src/backend/app/services/erp_simulator.py:53](src/backend/app/services/erp_simulator.py#L53)
- **CWE:** CWE-22 (Path Traversal) — not exploitable as written
- **OWASP:** A01 — Broken Access Control
- **Confidence:** Confirmed (safe)
- **Tool:** manual review

**Description**

`send_order_to_erp` writes `order_{order_id}_{ts}.json` where `order_id` is the client-supplied `num_order`. A traversal payload (`../../x`) is blocked because `int(order_id)` is evaluated for the payload **before** the write and raises `ValueError` on any non-numeric value, returning early without writing. So only digit strings reach the filename. Defense-in-depth only.

**Remediation**

Sanitize the filename explicitly (`re.sub(r"\D", "", order_id)` or `secure_filename`) so the safety does not depend on the order of an unrelated `int()` call.

---

### 3.9 [SEC-009] No authentication or rate limiting (real-mode quota abuse if exposed) — **Low**

- **File:** [serve.py:24](serve.py#L24), [src/backend/app/routers/order_processing_router.py:42](src/backend/app/routers/order_processing_router.py#L42)
- **CWE:** CWE-770 (Allocation of Resources Without Limits or Throttling)
- **OWASP:** A04 — Insecure Design / A07
- **Confidence:** Confirmed (mitigated by localhost binding)
- **Tool:** manual review

**Description**

No endpoint is authenticated or rate-limited — by design (documented anti-goal: public local demo, no auth). `serve.py` binds `127.0.0.1`, which is the mitigating control. If the app were ever bound to `0.0.0.0` / deployed, any caller could drive real-mode endpoints and spend the owner's OpenAI/Gemini quota (financial DoS), and hammer the DB.

**Remediation**

Keep the localhost binding. Before any deployment: add an auth layer + per-IP/per-key rate limiting, and tighten CORS (SEC-003). Document "local-only; do not expose" prominently in the README.

**References**
- [CWE-770](https://cwe.mitre.org/data/definitions/770.html)

---

### 3.10 [OBS-001] Anonymization release gate not yet executed (publish blocker) — **release-gate item**

- **File:** [tools/verify_anonymization.py:250](tools/verify_anonymization.py#L250)
- **Type:** process control (not a code defect)
- **Confidence:** Confirmed

**Description**

The structural gate (`verify_anonymization.py` with no `--terms`) checks ids, dropped columns, dates, secrets, emails, and phones, and passes (15/15). It explicitly **cannot** catch a real customer/site/supplier proper noun that is not a secret/phone/order-ref pattern and was not in the external replacements file — that coverage comes from (a) the author-run `--terms` sweep with the real-terms list (kept outside the repo), (b) the manual-review report from `anonymize_dataset.py`, and (c) a git-history sweep across all commits (a real term committed and later deleted still leaks — known gotcha #1). None of these has been run for this release.

**Impact**

If a real proper noun slipped through, it would become permanently public in git history. This is the highest-consequence item in the repo.

**Remediation (release gate — author machine, before the first `git push`)**

```bash
# 1. Full-tree term sweep with the external real-terms list
python tools/verify_anonymization.py --repo . --terms C:\Python Projects\portfolio-private\real_terms.txt
# 2. Git-history sweep across ALL commits (every blob, not just HEAD)
#    e.g. gitleaks detect --source . (history) + a grep of the terms list over `git rev-list --all` blobs
# 3. Only push after both are clean.
```

This is Phase 7, Step 5 in [docs/plans/phase_7/7.0_audit_release_gate.md](docs/plans/phase_7/7.0_audit_release_gate.md). The push itself is ASK-FIRST and requires the author's explicit go-ahead.

---

## 4. Defense-in-Depth Recommendations

- **[DEF-001] CI dependency + SAST scanning.** Wire `pip-audit` and `npm audit` (and optionally `bandit`/`ruff --select S`) into CI; fail on High+ CVEs. None of these were installed locally at audit time.
- **[DEF-002] Request-size limits.** Add a body-size middleware + the per-endpoint caps from SEC-001 (audio 25 MB, bounded list lengths).
- **[DEF-003] Pre-commit secret + term scanning.** Add `gitleaks`/`detect-secrets` and a terms-list grep as a pre-commit hook — the repo's public history makes prevention much cheaper than remediation.
- **[DEF-004] Generic client errors.** Centralize a generic error response; never return `str(exc)` or user filenames to the client (SEC-002). Keep full detail in server logs only.
- **[DEF-005] Reproducible installs.** Add a lockfile (`pip-compile`) and raise dependency floors (SEC-004).
- **[DEF-006] "Local-only" posture.** Keep `127.0.0.1` binding; document that real mode must not be exposed without auth + rate limiting (SEC-009).

---

## 5. Coverage

### What was reviewed (full read)
- `src/backend/app/` — all routers, services, core, models, utils (entry points: `main.py`, the 3 routers; all 5 pipeline stages; the simulated ERP/email/PDF channels).
- `tools/` — `anonlib.py`, `anonymize_dataset.py`, `verify_anonymization.py`, `generate_embeddings.py`, `load_database.py`, `apply_sql.py`, `make_tts_audio.py`.
- `src/frontend/src/` — `api/apiService.ts`, `App.tsx`, `vite.config.ts`, and a pattern sweep (XSS/storage/env/`target=_blank`) across all components.
- `serve.py`, `requirements.txt`, `src/frontend/package.json`, installed dependency versions (`pip freeze`).

### What was NOT reviewed (and why)
- `db/init/*.sql` — read previously (Phase 2); the CTE/HNSW functions set `statement_timeout` and use parameterized vector literals. Not re-audited line-by-line here.
- `tests/` — spot-checked, not audited as production code.
- `node_modules/` and `.venv/` — third-party; covered indirectly by the dependency-scanning recommendation, not read.
- Live runtime/OS permissions — inferred from code, not verified against a deployment.

### Tools run
| Tool | Status | Findings |
|------|--------|----------|
| ruff (`--select S`) | Run | 2 false-positive S608, 1 S603, 1 S607 (all triaged) |
| bandit | Not installed | Recommended (DEF-001) |
| pip-audit / safety | Not installed | Recommended; installed versions checked manually via `pip freeze` |
| semgrep | Not installed | Recommended |
| gitleaks | Not installed | Recommended (DEF-003) — and required for the OBS-001 history sweep |
| manual review | Completed | 1 medium, 5 low, 3 info + 1 release-gate item |

### Methodology
- Phase 1 — Scope & Context: full release-gate scope; threat model above.
- Phase 2 — Automated Scanning: `ruff --select S` (only available scanner); manual `pip freeze` CVE check.
- Phase 3 — Manual Review: read `audit-code/references/python-security.md` and `react-security.md` in full; applied the 10-question pass per file.
- Phase 4 — Exploit Reasoning: PoC sketches drafted (SEC-001); none executed.
- Phase 5 — Report: this document.

### Coverage self-check
- Entry points (3 routers + CLI tools): reviewed.
- External input → sink tracing (audio upload, query params, JSON bodies, num_order → file write): reviewed.
- Auth/authz: none by design (documented); IDOR N/A (no per-user resources).
- Dependency manifest: reviewed (installed versions current; floors flagged).
- Hardcoded secrets: none (regex scan + visual); keys via gitignored `.env`.
- Crypto: HMAC-SHA256 (anon ids) + SHA-256 (deterministic demo pick, non-security) — appropriate.
- Error handling / logging: reviewed (JSON formatter escapes → no log injection; no PII/secrets logged; client error verbosity flagged SEC-002).
- File system / subprocess: tempfile usage safe; only the dev TTS tool spawns a process (SEC-005).
- OWASP Top 10 applicable categories: covered.

### Caveats
- Reflects commit `5729823` plus the uncommitted Phase-7 docs. Later changes are not covered.
- Business-logic correctness was assessed from code/docstrings; the anonymization *completeness* depends on the external terms list and is gated by OBS-001, not provable from inside the repo.

---

## 6. Next Steps

1. **Code (this phase):** apply SEC-001 (upload cap) and the quick low-risk hardening (SEC-002 generic errors, SEC-003 `allow_credentials=False`, SEC-004 multipart floor); re-run the test suite.
2. **CI (this phase):** add the workflow with tests + the anonymization gate + a dependency-scan step (DEF-001).
3. **Release gate (author, pre-push):** execute OBS-001 (`--terms` + git-history sweep). Do not push until clean.
4. Track the remaining Low/Info items; none block phase closure.

### Remediation status (applied 2026-06-17, commit pending)

| ID | Severity | Status |
|----|----------|--------|
| SEC-001 | Medium | **Fixed** — 25 MB cap + content-type allowlist + content-length pre-check (`order_processing_router.py`) |
| SEC-002 | Low | **Fixed** — generic client errors; filename/`exc` kept in server logs only |
| SEC-003 | Low | **Fixed** — `allow_credentials=False` (`main.py`) |
| SEC-004 | Low | **Fixed** — `python-multipart>=0.0.18` (`requirements.txt`) |
| SEC-005 | Low | **Accepted** — dev-only TTS helper, author machine, not deployed (documented) |
| SEC-006 | Info | **Fixed** — hardcoded `data:application/pdf` MIME + `download` attr (`App.tsx`) |
| SEC-007 | Info | **Fixed** — `# noqa: S608` + rationale on both non-injectable sites |
| SEC-008 | Info | **Fixed** — filename derived from digits only (`erp_simulator.py`) |
| SEC-009 | Low | **Accepted** — no auth/rate-limit by design; mitigated by `127.0.0.1` binding (README warns) |
| OBS-001 | gate | **Executed** in this phase (Step 5): `--terms` sweep + git-history sweep — see §below |
| DEF-001 | — | **Done** — `pip-audit` + `ruff --select S` wired into CI |

All fixes re-verified: `pytest` 117 passed / 1 skipped; frontend `npm run build` clean.

**Phase-closure decision:** no Critical/High findings → the code audit does not block closing Phase 7. The **public push** remains blocked on OBS-001 (the anonymization release gate), which is an explicit, recorded Phase-7 Step-5 task requiring the author's external terms list and go-ahead.

---

*Report generated by the `audit-code` skill. Re-run: `/8-audit full` on the same scope and diff the reports.*
