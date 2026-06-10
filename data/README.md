# data/ — real, anonymized dataset

Real operational data from a voice-ordering system in production, published after an irreversible,
verifiable anonymization process (criteria: `docs/refs/legal-framework-anonymization.md`;
process: `workflows/anonymize_dataset.md`; gate: `tools/verify_anonymization.py`).

The dictated text and article descriptions are in **Spanish** — the system operates in Spanish for
Spanish field technicians, and the text is kept verbatim because it *is* the matching problem this
project demonstrates.

| File | Content | Rows |
|------|---------|------|
| `catalog.csv` | article catalog (anonymized id, verbatim description, last purchase by month) | 31069 |
| `historical.csv` | learned memory: dictated phrase (sanitized) -> confirmed article | 974 |
| `extraction_pairs.jsonl` | validated pairs (sanitized transcription -> expected items) | 47 |

## What was changed

- **Article ids**: regenerated as `ART-<10hex>` via HMAC-SHA256 with a secret salt kept outside the
  repository (same real article -> same token across all files; irreversible without the salt).
- **Dictated text**: end-customer/site names -> `[customer]`/`[site]`; order references ->
  `[order-ref]`; phone numbers -> `[phone]`.
- **Catalog descriptions**: the real catalog contains administrative rows embedding people's names,
  phone numbers, the supplier and end-customer names - those terms are sanitized to
  `[person]`/`[phone]`/`[supplier]`/`[customer]` (numeric specs such as DIN/UNE norm numbers are
  never touched).
- **Dropped columns**: supplier, order numbers, user ids, precise timestamps (dates reduced to
  `YYYY-MM`).
- **Dropped rows** (unpublishable or breaking referential integrity): catalog
  1 without id + 0 duplicate ids; historical
  27 without catalog id + 0 orphan ids.

## What was NOT changed

Article descriptions and the dictated technical text (measures, materials, trade slang) are
verbatim: they are the real matching problem this project demonstrates. The real catalog's "dirty"
rows (empty or administrative descriptions) are kept on purpose.

## What is not published

No audio of any kind (voice is biometric data), no real identifier, no row that failed the process.
The real-terms list and the salt live outside the repository.
