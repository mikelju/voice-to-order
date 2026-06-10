# Workflow: regenerate the anonymized dataset (author only)

## Goal
Regenerate `data/` from the real sources whenever the source data or the anonymization rules change,
and prove the result clean before committing.

## Inputs (all OUTSIDE the repo)
- `REAL_DATA_DIR` — folder with the real CSV/JSONL files
- `ANON_SALT` — secret salt (same value across runs, or every id token changes)
- `REAL_REPLACEMENTS_FILE` — `term=>token` mapping of real names
- The real-terms list for the sweep (`--terms`)

## Steps
1. Export the three environment variables (values from the private vault, never from the repo).
2. Run `python tools/anonymize_dataset.py` — writes `data/` + `.tmp/manual_review.txt`.
3. **Read `.tmp/manual_review.txt`** (blocking): every candidate is either
   (a) a new real name → add it to the private replacements + terms files and go to step 2, or
   (b) a public brand / domain word / number word → leave it.
4. Run the full gate:
   `python tools/verify_anonymization.py data --repo . --terms <private terms file>` → must end
   `0 FAIL`.
5. Commit `data/` only after step 4 is green.

## Error handling
- Tool aborts on HMAC collision (two real ids → same token): widen the token or investigate.
- A `[FAIL]` in the sweep usually means a NEW Whisper spelling of a known site/customer — add the
  variant to the private files, regenerate, re-verify.

## Learnings
- Whisper invents a new spelling of the same site name per audio (three variants of one site found
  in the first real run); the manual-review report is what catches them, not the lists.
- The real catalog embeds PII in administrative rows (a contact name + phone number); that is why
  descriptions also pass through term+phone sanitization and the gate has a phone check.
