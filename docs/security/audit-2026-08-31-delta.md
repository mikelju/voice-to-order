# Security Audit (delta) — Voice-to-Order

**Date:** 2026-08-31 · **Mode:** `/8-audit` delta — everything changed since the release-gate
audit `audit-2026-06-17-full.md` · **Skill:** `.claude/skills/audit-code/`

## 1. Executive summary

Scope is small and mostly non-runtime: a frontend i18n layer with no new dependency, one new
CLI tool, new tests, a licence and documentation. **The backend attack surface is unchanged** —
no router, service, model or SQL was touched since the full audit, so its findings and their
remediation status still stand.

One real finding, in the gate tooling itself rather than in the product: the history sweep
treated a failing `git` invocation as an empty result, which would have reported a **false
CLEAN**. Fixed in this pass. It is the same failure mode that made the first `git filter-repo`
run look successful while changing nothing — a check that cannot run must never look like a
check that passed.

| Severity | Count |
|---|---|
| Critical | 0 |
| High     | 0 |
| Medium   | 0 |
| Low      | 1 (fixed) |
| Info     | 2 |

## 2. Findings

### 2.1 [SEC-010] History sweep reported CLEAN when `git` failed — **Low** (fixed)

- **File:** `tools/history_sweep.py`
- **CWE:** CWE-754 (Improper Check for Unusual or Exceptional Conditions)

`run()` returned `proc.stdout` without inspecting `returncode`. Pointed at a directory that is
not a git repository, at a corrupted repo, or run where `git` is missing, the sweep saw zero
blobs and printed `[OK] git-history sweep CLEAN` with exit code 0. This is a pre-publication
gate: a false green here is the worst possible failure, because it authorises a push.

**Fix applied:** `run()` raises `GitError` on non-zero exit; `main()` catches it and exits **2**
(distinct from 0 CLEAN and 1 FAIL). An empty terms list also exits 2 rather than sweeping for
nothing. Covered by `tests/tools/test_history_sweep.py::test_non_git_directory_errors_instead_of_reporting_clean`
and `::test_empty_terms_list_errors`.

### 2.2 [SEC-011] Frontend i18n layer — **Info** (no action)

- **Files:** `src/frontend/src/i18n.tsx` + the 11 components consuming `t()`

Reviewed for the usual injection paths: no `dangerouslySetInnerHTML`, no `innerHTML`, no `eval`,
no `document.write`. Interpolation is `String.split().join()` over dictionary values, rendered as
React children, so React escapes it. `localStorage` holds one value, read back through an
explicit allowlist (`saved === 'es' || saved === 'en'`) — a tampered `vto_lang` cannot become a
language, and both accesses are wrapped in `try/catch` so a blocked storage degrades instead of
throwing. Dictionary values are static literals, not user or server content.

### 2.3 [SEC-012] Test-only subprocess use — **Info** (no action)

`tests/tools/test_history_sweep.py` shells out to `git` to build throwaway repositories under
`tmp_path`. Argument lists (never `shell=True`), fixed literals, no user input, no network. The
stand-in term used in the tests is fictional and is never a real term.

## 3. Dependencies

No dependency was added: the i18n layer is deliberately dependency-free, and `git-filter-repo`
was a one-off local tool, never added to `requirements.txt`. CI (`pip-audit` + `npm audit`) is
green on the current tree.

## 4. Coverage

**Reviewed (full read):** `tools/history_sweep.py`, `src/frontend/src/i18n.tsx`,
`tests/tools/test_history_sweep.py`, `tests/frontend/test_i18n_parity.py`, `LICENSE`,
`README.md` diff, `.github/workflows/ci.yml` (unchanged).

**Not re-reviewed (and why):** `src/backend/**` — untouched since `audit-2026-06-17-full.md`
(verified by diff); its Low/Info items (SEC-005 dev TTS helper, SEC-009 no auth by design)
remain accepted with the same rationale.

**Process events since the last audit, verified rather than assumed:**

- git history rewritten to remove a real end-customer term (`fixes/fix-2`); full-history sweep
  CLEAN, working-tree `--terms` gate 17 checks / 0 FAIL.
- the live repository re-created from the clean history, because a force-push leaves the old
  objects reachable by SHA; verified that pre-rewrite SHAs now 404 on the live repo.

## 5. Result

**No Critical/High/Medium.** The single Low is fixed and covered by tests. Nothing blocks
publication from a security standpoint.
