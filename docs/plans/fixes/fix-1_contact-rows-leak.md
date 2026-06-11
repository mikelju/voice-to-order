# Fix 1: personal data leak in catalog "CONTACTO:" admin rows

> One-off corrective (protocol: `docs/plans/0_master_plan.md` → Fixes).
> Affects Phase 1 functionality (anonymized dataset + verification).

## Bug description

`data/catalog.csv` (published dataset) still contains **64 administrative rows** of the form
`CONTACTO: <real person name> - <phone> -llamar en horario de 7:00h a 15:00h-` with:

- Real **person names** (and at least one end-customer company name) un-tokenized.
- **23 phone numbers in spaced format** (`6XX XX XX XX` / `6XX XXX XXX`) that `PHONE_RE`
  (`\b[679]\d{8}\b`, contiguous digits only) does not capture.

Found during the Phase-3 preparation sweep (full mapping of the original system). The repo has
not been pushed publicly yet, so the leak is contained to the local machine.

## Root cause

1. `PHONE_RE` only matched 9 contiguous digits; real admin rows use grouped/spaced phones.
2. Person names inside catalog descriptions were only covered by the external replacements
   list, which did not include the contact names; and `proper_noun_candidates` is deliberately
   not run over the 31k ALL-CAPS catalog descriptions, so the manual-review report never
   surfaced them.

## Adopted solution (layered)

1. **`PHONE_RE` extended** to capture Spanish 9-digit numbers with optional space/dot
   separators in the common groupings (3-3-3, 3-2-2-2) in addition to contiguous.
   Over-matching in technical specs is acceptable (privacy > precision in admin rows).
2. **New structural rule `CONTACT_RE`** in `sanitize_text`: after `CONTACTO:?`, any run of
   name-like text (no digits, no `[` tokens) is replaced by `[person] `. This sanitizes any
   contact name structurally, with no dependence on the external names list.
3. External replacements list (outside the repo) extended with the company names found next
   to contacts.
4. `tools/verify_anonymization.py` gains a **structural gate**: any `CONTACTO` row that still
   contains a capitalized word other than the `[person]`/`[phone]`/... tokens fails the check.
5. Dataset regenerated (`tools/anonymize_dataset.py`), verified, and reloaded into the DB.

Note: the pre-fix dataset exists in the local git history. The history sweep before the first
public push (Phase 7 release gate) must squash/rewrite history so the leaked rows never reach
the public remote.

## Modified files

- `tools/anonlib.py` — extended `PHONE_RE`, new `CONTACT_RE` + step in `sanitize_text`
- `tools/verify_anonymization.py` — structural CONTACTO gate
- `tests/tools/test_anonlib.py`, `tests/tools/test_verify_anonymization.py` — new tests
- `data/catalog.csv` (+ `data/README.md` counters) — regenerated
- (outside repo) `voice-to-order-replacements.txt` — company names added
