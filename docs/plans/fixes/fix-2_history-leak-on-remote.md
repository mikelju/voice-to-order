# Fix 2: real term (end-customer company name) in git history — FIXED (history rewritten)

> One-off corrective. Affects Phase 1 / Phase 7 (anonymization release gate).
> **Status: FIXED — 2026-08-31.** The history was rewritten with `git filter-repo`, the
> full-history sweep reports CLEAN, and the live repository was re-created from the clean
> history so that not even unreachable pre-rewrite objects survive. This **supersedes the
> 2026-06-13 WON'T FIX decision** — see [Decision history](#decision-history).
>
> **Redaction note (2026-08-31):** the real term is deliberately **not** written in this
> file, nor anywhere else in the repo. Naming it here re-introduced the very leak this
> document reports (it broke the `--terms` release gate: 1 FAIL over `0_master_plan.md`
> and this file). It lives only in the external terms/replacements lists
> (`portfolio-private/`). Below it is called "the leaked term".

## Bug description

The Phase-7 git-history sweep (every blob in every commit, not just HEAD) found a real
end-customer company name inside `data/catalog.csv` in the pre-fix-1 commits. The working
tree (HEAD) was already clean — fix-1 sanitized those rows and regenerated the dataset —
but the pre-fix-1 blob still lived in history. This is exactly known-gotcha #1
(`CLAUDE.md`): "a real term committed and later deleted remains in history."

**Full inventory, measured per term on 2026-08-31.** Pre-rewrite SHAs are deliberately
**not listed here**: those objects are unreachable but still served by GitHub until its
own gc runs (see [Residual exposure](#residual-exposure)), so a SHA in a public file is a
direct pointer to the leaked blob.

| Where | Scope |
|---|---|
| `data/catalog.csv` (blob) | 1 term, 2 case variants, 4 occurrences · the Phase-1 and Phase-2 commits (pre-fix-1) |
| `0_master_plan.md`, `fix-2_*.md` (blobs) | same term · the two Phase-7 closure commits and the i18n commit |
| Commit messages | Phase-7 closure commit (subject + body), Phase-7 release-gate commit (body) |
| Working tree at HEAD | clean (since the redaction commit) |

Two corrections to the original 2026-06-13 write-up:

1. **It was one term, not two.** `.tmp/history_sweep.py` counts *variants* but labels them
   `term(s)`, so its `catalog.csv: 2 term(s)` line read as two distinct real names. They
   were two case variants of the same one.
2. **The scope had grown.** The 2026-06-13 note described two commits carrying one CSV
   blob. By 2026-08-31 the fix-2 document itself had spread the term to two more `.md`
   files across three more commits, plus two commit messages — the document reporting the
   leak had become the largest carrier of it.

## Root cause

fix-1 corrected the working tree and reloaded the DB, but did not rewrite history; the
leaked commits had already been pushed. The pre-push history sweep that would have caught
this (Phase 7, Step 5) ran only after those commits were on the remote.

## Impact

The leaked term is a real company name (an end customer of the original client) — precisely
what the anonymization exists to remove. Exposure was bounded: the GitHub repository has
been **private** since creation (`2026-06-11`), with `forks_count: 0`, `network_count: 0`
and one subscriber (the author). No fork or third-party clone could retain the old objects.

## Decision history

1. **2026-06-13 — WON'T FIX (risk accepted).** Rationale: the term is a company name, not
   personal data (fix-1 had already sanitized person names and phone numbers), and
   "rewriting *public* history is not worth the cost".
2. **2026-08-31 — reopened and fixed.** The premise of that decision did not hold: the
   remote was never public, and with zero forks a rewrite costs one command and reaches
   every copy that exists. Meanwhile the scope had grown (see the inventory above) and the
   repo's whole purpose is to eventually *be* published — which would have published the
   history along with it. Author's decision: rewrite and force-push.

## Adopted solution — APPLIED 2026-08-31

1. **Backups first:** `git bundle create <scratchpad>/vto-pre-rewrite.bundle --all` (20 MB,
   full pre-rewrite history) plus a `backup/pre-history-rewrite` branch.
2. **Redact the working tree first** (the redaction commit) so the rewrite had a clean HEAD
   to converge on.
3. **Rewrite** with `git filter-repo`, applying the same replacement file to blob contents
   and to commit messages:
   ```bash
   pip install git-filter-repo            # local tool, not a project dependency
   python -m git_filter_repo \
       --replace-text  <file> \           # one "<variant>==>[customer]" line per variant
       --replace-message <file> \         # same file: also sanitizes commit messages
       --force
   ```
   The replacement file is generated from the external terms list, lives outside the repo,
   and was deleted afterwards.
4. **Restore the remote** (`filter-repo` removes `origin` by design) and **remap the SHAs
   quoted in the docs** from `.git/filter-repo/commit-map`.
5. **Force-push** `main` with `--force-with-lease`.
6. **Re-create the live repository** from the clean history, so no unreachable pre-rewrite
   object survives where the repo will be published (see Residual exposure).

## Residual exposure — closed 2026-08-31

A force-push deletes nothing on GitHub. The pre-rewrite commits became unreachable but were
**still served by SHA** through the API and the web UI — verified right after the push: the
old SHAs still resolved. A rewrite alone would therefore not have been enough to publish.

What closed it:

1. The old repository was **renamed** to `voice-to-order-archive-pre-rewrite`, left
   **private** and **archived** (read-only). It still holds the unreachable objects, and
   nothing in it will ever be published.
2. A **new, empty** `voice-to-order` repository was created and the rewritten history pushed
   into it. A fresh repository cannot serve objects that were never pushed to it.
3. **Verified:** in the live repository every pre-rewrite SHA now returns `404 No commit found
   for SHA`, while the rewritten history resolves normally. CI is green on the new repo.

Deleting the archived repository is optional cleanup (no issues, no PRs, no forks), not a
prerequisite for publishing. The pre-rewrite SHAs are still deliberately absent from this
document: they are pointers to objects that exist in that archive.

## Verification

| Check | Result |
|---|---|
| `.tmp/history_sweep.py` over all blobs | **CLEAN** — no real term in any blob of any commit |
| `verify_anonymization.py --repo . --terms <external>` | 17 checks, **0 FAIL** |
| Structural gate (CI-runnable) | 15 checks, 0 FAIL |
| HEAD tree hash, pre vs post rewrite | identical (`7b5ce50`) — no working-tree content changed |
| Commit count | 19 before, 19 after — no commit dropped |
| Test suite | 117 passed, 1 skipped |

## Operational lessons

- **A silent no-op looks exactly like success.** The first `filter-repo` run used a
  `regex:` line written with CRLF endings; it exited 0, printed "New history written", and
  changed nothing (HEAD kept its SHA — the tell). Rewriting with one *literal* line per
  variant and LF endings worked. Never trust the exit code here: verify with the sweep.
- **Release-gate tooling must be versioned.** `history_sweep.py` lived in `.tmp/`
  (untracked) and mislabelled variants as terms — which is how this document's inventory
  came to claim two real names when there was one. Fixed 2026-08-31: it is now
  `tools/history_sweep.py`, with the label corrected, commit messages swept as well as
  blobs, output that never prints a matched term, and six tests.
- **Documenting a leak by quoting it re-creates it.** See the redaction note above.

## Modified files

- `docs/plans/fixes/fix-2_history-leak-on-remote.md` — this file (won't-fix -> fixed)
- `docs/plans/0_master_plan.md` — Phase 7 history-sweep item now closed
- git history — rewritten (every SHA changed); pre-rewrite SHAs quoted in docs remapped
- the GitHub repository — re-created from the clean history; the pre-rewrite one archived
- (done, outside repo) `voice-to-order-replacements.txt`, `voice-to-order-terms.txt` — term added
