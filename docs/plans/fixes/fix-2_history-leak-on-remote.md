# Fix 2: real term ("[customer]") in public git history — RISK ACCEPTED by the author

> One-off corrective. Affects Phase 1/Phase 7 (anonymization release gate).
> **Status: WON'T FIX (accepted risk). 2026-06-13 — the author reviewed the finding and
> decided the exposure is acceptable: "[customer]" is a company name (not personal data;
> person names and phone numbers WERE sanitized by fix-1), and rewriting public history
> is not worth the cost here. No history rewrite / force-push will be performed.**
>
> The working tree stays clean (the term is in the external replacements/terms lists, so
> any dataset regeneration re-sanitizes it). Recorded for traceability per the framework's
> "explicit decision to defer with justification" rule.

## Bug description

The Phase-7 git-history sweep (every blob in every commit, not just HEAD) found a real
end-customer company name, **"[customer]"**, inside `data/catalog.csv` in two commits:

- `c5a2e30` — "Phase 1: anonymized dataset + verification gate"
- `e295387` — "Phase 2: local Postgres+pgvector ..."

The working tree (HEAD) is clean: fix-1 sanitized those rows and regenerated the dataset.
But the **pre-fix-1 blob still lives in history**, and both commits are ancestors of
`origin/main` (`fbbe73e` = fix-1). Confirmed:

```
git ls-remote --heads origin   ->  fbbe73e ... refs/heads/main
git merge-base --is-ancestor c5a2e30 fbbe73e  ->  true
git merge-base --is-ancestor e295387 fbbe73e  ->  true
```

So the leak is **already on the remote** `github.com/mikelju/voice-to-order.git`, not just
local. This is exactly known-gotcha #1 (`CLAUDE.md`): "a real term committed and later
deleted remains in history."

## Root cause

fix-1 corrected the working tree and reloaded the DB, but did not rewrite history; the
leaked commits had already been pushed (the remote was at fix-1, which descends from the
Phase-1/2 commits). The pre-push history sweep that would have caught this (Phase 7, Step 5)
ran only now — after those commits were public.

## Impact

"[customer]" is a real company name (an end customer of the original client) — precisely what
the anonymization exists to remove. While public, anyone can read it in the repo's history,
and GitHub may have cached/indexed the old commits; existing clones/forks retain them.

## Adopted solution — NOT YET APPLIED (needs author go-ahead)

Because remediation is **destructive** (rewrites every SHA) and **outward-facing** (force-push
to a public remote), it is not run autonomously. Recommended steps, in order:

1. **Decide repo visibility now.** If the GitHub repo is public, consider making it private
   until remediated (reduces exposure window). Confirm whether it was ever forked.
2. **Add "[customer]" to the external replacements + terms lists** (done already:
   `portfolio-private/voice-to-order-replacements.txt` and `-terms.txt`) so the working-tree
   gate stays clean and any regeneration re-sanitizes it.
3. **Rewrite history** so the leaked blob never appears. Cleanest given the dataset is a
   generated artifact: replace `data/catalog.csv` in every commit with the sanitized version,
   e.g. with `git filter-repo`:
   ```bash
   # back up first
   git branch backup/pre-history-rewrite
   # replace the leaked content across all commits (sanitized file = current HEAD version)
   git filter-repo --path data/catalog.csv --replace-text <(echo "[customer]==>[customer]")
   #   or, simpler and equally valid here: re-create the branch from a clean root
   #   (the SDD narrative can be preserved by re-committing the phase docs unchanged).
   ```
   Verify with the history sweep until it is clean:
   ```bash
   python tools/verify_anonymization.py --repo . --terms <external terms>
   python .tmp/history_sweep.py <external terms>   # must report CLEAN
   ```
4. **Force-push** the rewritten history (`git push --force-with-lease origin main`) — ONLY
   after the author approves (this is the single ASK-FIRST, irreversible step).
5. **Post-rewrite remote hygiene:** the old commits may persist on GitHub until garbage
   collected; consider contacting GitHub support to purge cached views, and rotate anything
   else that touched those commits. Document the outcome here.

## Verification of the rest

Everything else is green and does not depend on this fix:
- working-tree `--terms` sweep: 17 checks, 0 FAIL
- structural anonymization gate: 15/15
- test suite: 117 passed, 1 skipped
- demo + real E2E: verified

## Modified files

- `docs/plans/0_master_plan.md` — Phase 7 marked Blocked; this fix referenced
- (pending) git history — to be rewritten on author go-ahead
- (done, outside repo) `voice-to-order-replacements.txt`, `voice-to-order-terms.txt` — "[customer]" added
