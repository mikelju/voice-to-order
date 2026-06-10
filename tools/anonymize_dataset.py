# tools/anonymize_dataset.py
"""Generate data/ (the anonymized dataset) from the real source data.

ONLY runnable on the author's machine: it needs environment variables pointing at
resources that NEVER enter the repo:

    REAL_DATA_DIR           folder with the real CSV/JSONL files
    ANON_SALT               secret salt for the id HMAC
    REAL_REPLACEMENTS_FILE  'term=>token' file (real names -> [customer]/[site]/...)

Usage:
    python tools/anonymize_dataset.py [--output data]

Output: data/catalog.csv, data/historical.csv, data/extraction_pairs.jsonl,
data/README.md and .tmp/manual_review.txt (human-review report, blocking
before committing data/).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from anonlib import anon_id, load_replacements, proper_noun_candidates, sanitize_text, to_month

# File names inside REAL_DATA_DIR (carry no identifying information)
SRC_CATALOG = "articulos_proveedor.csv"
SRC_HISTORICAL = "historico_pedidos_rows.csv"
SRC_PAIRS = "fine-tuning/fine_tuning.jsonl"


def fail(msg: str) -> None:
    print(f"[ERROR] {msg}")
    sys.exit(2)


def read_env() -> tuple[Path, str, list[tuple[str, str]]]:
    real_dir = os.environ.get("REAL_DATA_DIR", "")
    salt = os.environ.get("ANON_SALT", "")
    repl_file = os.environ.get("REAL_REPLACEMENTS_FILE", "")
    if not real_dir or not Path(real_dir).is_dir():
        fail("REAL_DATA_DIR not set or does not exist (see docstring)")
    if not salt:
        fail("ANON_SALT not set (the salt lives OUTSIDE the repo)")
    if not repl_file or not Path(repl_file).is_file():
        fail("REAL_REPLACEMENTS_FILE not set or does not exist")
    return Path(real_dir), salt, load_replacements(repl_file)


def anonymize_catalog(real_dir: Path, salt: str, repl: list[tuple[str, str]],
                      out_dir: Path) -> tuple[dict[str, str], dict]:
    """Returns (real_id->token map, counters).

    Descriptions are kept verbatim EXCEPT term/phone sanitization: the real catalog
    contains administrative rows embedding people's names, phone numbers, the supplier
    and end-customer names. order_refs=False so numeric specs are never touched.
    """
    src = real_dir / SRC_CATALOG
    id_map: dict[str, str] = {}
    token_to_real: dict[str, str] = {}
    rows_out: list[dict] = []
    dropped_no_id = 0
    dropped_dup = 0
    with open(src, encoding="utf-8", errors="replace", newline="") as f:
        for row in csv.DictReader(f):
            real_id = (row.get("IdArticulo") or "").strip()
            desc = sanitize_text((row.get("Articulo") or "").strip(), repl, order_refs=False)
            # NOTE: no proper-noun heuristic over catalog descriptions - 31k ALL-CAPS
            # product rows would flood the report; the catalog is covered by the
            # terms sweep + the phone/secret structural checks instead.
            if not real_id:
                dropped_no_id += 1
                continue
            if real_id in id_map:
                dropped_dup += 1
                continue
            token = anon_id(real_id, salt)
            if token in token_to_real and token_to_real[token] != real_id:
                fail(f"HMAC collision between two distinct real ids on token {token} - aborting")
            token_to_real[token] = real_id
            id_map[real_id] = token
            rows_out.append({
                "id_articulo": token,
                "articulo": desc,
                "ultima_compra_mes": to_month(row.get("FechaUltimaCompra") or ""),
            })
    with open(out_dir / "catalog.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id_articulo", "articulo", "ultima_compra_mes"])
        w.writeheader()
        w.writerows(rows_out)
    counts = {"catalog_rows": len(rows_out), "catalog_dropped_no_id": dropped_no_id,
              "catalog_dropped_duplicate_id": dropped_dup}
    return id_map, counts


def anonymize_historical(real_dir: Path, salt: str, id_map: dict[str, str],
                         repl: list[tuple[str, str]], out_dir: Path,
                         review: set[str]) -> dict:
    src = real_dir / SRC_HISTORICAL
    rows_out: list[dict] = []
    dropped_no_id = 0
    dropped_orphan = 0
    with open(src, encoding="utf-8", errors="replace", newline="") as f:
        for row in csv.DictReader(f):
            real_id = (row.get("id_articulo_catalogo") or "").strip()
            if not real_id:
                dropped_no_id += 1
                continue
            if real_id not in id_map:
                dropped_orphan += 1
                continue
            user_text = sanitize_text((row.get("user_text") or "").strip(), repl)
            review |= proper_noun_candidates(user_text)
            rows_out.append({
                "user_text": user_text,
                "catalog_description": (row.get("catalog_description") or "").strip(),
                "id_articulo": id_map[real_id],
                "frequency": int(float(row.get("frequency") or 1)),
                "last_used_month": to_month(row.get("last_used") or ""),
            })
    with open(out_dir / "historical.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["user_text", "catalog_description", "id_articulo",
                                          "frequency", "last_used_month"])
        w.writeheader()
        w.writerows(rows_out)
    return {"historical_rows": len(rows_out), "historical_dropped_no_id": dropped_no_id,
            "historical_dropped_orphan_id": dropped_orphan}


def anonymize_pairs(real_dir: Path, repl: list[tuple[str, str]], out_dir: Path,
                    review: set[str]) -> dict:
    src = real_dir / SRC_PAIRS
    n = 0
    with open(src, encoding="utf-8") as fin, \
            open(out_dir / "extraction_pairs.jsonl", "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            msgs = {m["role"]: m["content"] for m in rec["messages"]}
            transcription = sanitize_text(msgs["user"].strip(), repl)
            review |= proper_noun_candidates(transcription)
            items = []
            for ln in msgs["assistant"].splitlines()[1:]:
                ln = ln.strip()
                if not ln:
                    continue
                parts = ln.rsplit(",", 1)
                if len(parts) == 2:
                    desc, qty = parts[0].strip(), parts[1].strip()
                    items.append({"qty": qty, "description": sanitize_text(desc, repl)})
            fout.write(json.dumps({"transcription": transcription, "expected_items": items},
                                  ensure_ascii=False) + "\n")
            n += 1
    return {"extraction_pairs": n}


README_TEMPLATE = """# data/ — real, anonymized dataset

Real operational data from a voice-ordering system in production, published after an irreversible,
verifiable anonymization process (criteria: `docs/refs/legal-framework-anonymization.md`;
process: `workflows/anonymize_dataset.md`; gate: `tools/verify_anonymization.py`).

The dictated text and article descriptions are in **Spanish** — the system operates in Spanish for
Spanish field technicians, and the text is kept verbatim because it *is* the matching problem this
project demonstrates.

| File | Content | Rows |
|------|---------|------|
| `catalog.csv` | article catalog (anonymized id, verbatim description, last purchase by month) | {catalog_rows} |
| `historical.csv` | learned memory: dictated phrase (sanitized) -> confirmed article | {historical_rows} |
| `extraction_pairs.jsonl` | validated pairs (sanitized transcription -> expected items) | {extraction_pairs} |

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
  {catalog_dropped_no_id} without id + {catalog_dropped_duplicate_id} duplicate ids; historical
  {historical_dropped_no_id} without catalog id + {historical_dropped_orphan_id} orphan ids.

## What was NOT changed

Article descriptions and the dictated technical text (measures, materials, trade slang) are
verbatim: they are the real matching problem this project demonstrates. The real catalog's "dirty"
rows (empty or administrative descriptions) are kept on purpose.

## What is not published

No audio of any kind (voice is biometric data), no real identifier, no row that failed the process.
The real-terms list and the salt live outside the repository.
"""


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate data/ from the real sources (author only)")
    ap.add_argument("--output", default="data")
    args = ap.parse_args()

    real_dir, salt, repl = read_env()
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    review: set[str] = set()

    id_map, c1 = anonymize_catalog(real_dir, salt, repl, out_dir)
    c2 = anonymize_historical(real_dir, salt, id_map, repl, out_dir, review)
    c3 = anonymize_pairs(real_dir, repl, out_dir, review)
    counts = {**c1, **c2, **c3}

    (out_dir / "README.md").write_text(README_TEMPLATE.format(**counts), encoding="utf-8")

    tmp = Path(".tmp")
    tmp.mkdir(exist_ok=True)
    report = tmp / "manual_review.txt"
    report.write_text(
        "Proper-noun candidates after sanitization (review BEFORE committing data/):\n"
        + "\n".join(f"  - {c}" for c in sorted(review)) + "\n",
        encoding="utf-8")

    for k, v in counts.items():
        print(f"[OK] {k} = {v}")
    print(f"[OK] manual review report: {report} ({len(review)} candidates)")
    print("[WARN] Review the report and run tools/verify_anonymization.py --terms before committing")


if __name__ == "__main__":
    main()
