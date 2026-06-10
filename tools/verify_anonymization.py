# tools/verify_anonymization.py
"""Runnable anonymization gate over data/ (and optionally the whole repo).

Anyone can run the public mode (structural checks + secret scan):

    python tools/verify_anonymization.py            # verify data/
    python tools/verify_anonymization.py --repo .   # + secret sweep over the whole repo

The author additionally runs the sweep with the real-terms list (kept outside the repo):

    python tools/verify_anonymization.py --terms <path-outside-the-repo>

Exit code 0 = every check PASS. Non-zero = at least one FAIL.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from anonlib import ID_TOKEN_RE, MONTH_RE, ORDER_REF_RE, PHONE_RE

SECRET_PATTERNS = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS key"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "OpenAI-style key"),
    (re.compile(r"AIza[0-9A-Za-z_\-]{35}"), "Google API key"),
    (re.compile(r"gh[posru]_[A-Za-z0-9]{30,}"), "GitHub token"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key"),
    (re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"), "JWT"),
    (re.compile(r"(?:postgres|mysql|mongodb)(?:\+\w+)?://[^\s\"']+:[^\s\"'@]+@"), "DB conn string"),
]
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@(?!example\.com)[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
FORBIDDEN_COLUMNS = {"ultimoproveedor", "order_number", "user_id", "created_at",
                     "confidence_score", "fechaultimacompra"}
TEXT_EXT = {".md", ".py", ".json", ".jsonl", ".txt", ".csv", ".sql", ".yml", ".yaml",
            ".toml", ".ts", ".tsx", ".js", ".html", ".css", ".env"}


class Report:
    def __init__(self) -> None:
        self.items: list[tuple[bool, str, str]] = []

    def add(self, ok: bool, name: str, detail: str = "") -> None:
        self.items.append((ok, name, detail))

    def dump_and_exit(self) -> None:
        fails = 0
        for ok, name, detail in self.items:
            mark = "[PASS]" if ok else "[FAIL]"
            line = f"  {mark} {name}"
            if detail:
                line += f" - {detail}"
            print(line)
            fails += 0 if ok else 1
        print(f"\n  {len(self.items)} checks | {fails} FAIL")
        sys.exit(1 if fails else 0)


def variants(term: str) -> set[str]:
    t = term.strip()
    if not t:
        return set()
    deacc = "".join(c for c in unicodedata.normalize("NFKD", t)
                    if not unicodedata.combining(c))
    base = {t, t.lower(), t.upper(), t.title(), deacc, deacc.lower()}
    more = set()
    for b in list(base):
        more |= {b.replace(" ", "_"), b.replace(" ", "-"), b.replace(" ", "")}
    return {v for v in base | more if len(v) >= 3}


def check_catalog(path: Path, r: Report) -> set[str]:
    ids: set[str] = set()
    if not path.is_file():
        r.add(False, "catalog.csv exists")
        return ids
    bad_id = bad_month = dup = 0
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        cols = {c.lower() for c in (reader.fieldnames or [])}
        r.add(not (cols & FORBIDDEN_COLUMNS), "catalog: no forbidden columns",
              str(cols & FORBIDDEN_COLUMNS))
        for row in reader:
            tok = row.get("id_articulo", "")
            if not ID_TOKEN_RE.match(tok):
                bad_id += 1
            if tok in ids:
                dup += 1
            ids.add(tok)
            m = row.get("ultima_compra_mes", "")
            if m and not MONTH_RE.match(m):
                bad_month += 1
    r.add(bad_id == 0, "catalog: every id is an ART-<10hex> token", f"{bad_id} invalid")
    r.add(dup == 0, "catalog: ids are unique", f"{dup} duplicates")
    r.add(bad_month == 0, "catalog: dates are YYYY-MM only", f"{bad_month} invalid")
    return ids


def check_historical(path: Path, catalog_ids: set[str], r: Report) -> None:
    if not path.is_file():
        r.add(False, "historical.csv exists")
        return
    orphan = bad_month = order_refs = 0
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        cols = {c.lower() for c in (reader.fieldnames or [])}
        r.add(not (cols & FORBIDDEN_COLUMNS), "historical: no forbidden columns",
              str(cols & FORBIDDEN_COLUMNS))
        for row in reader:
            if row.get("id_articulo") not in catalog_ids:
                orphan += 1
            m = row.get("last_used_month", "")
            if m and not MONTH_RE.match(m):
                bad_month += 1
            if ORDER_REF_RE.search(row.get("user_text", "")):
                order_refs += 1
    r.add(orphan == 0, "historical: referential integrity with catalog", f"{orphan} orphans")
    r.add(bad_month == 0, "historical: dates are YYYY-MM only", f"{bad_month} invalid")
    r.add(order_refs == 0, "historical: no order references left in user_text",
          f"{order_refs} leftovers")


def check_pairs(path: Path, r: Report) -> None:
    if not path.is_file():
        r.add(False, "extraction_pairs.jsonl exists")
        return
    bad_json = order_refs = 0
    n = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            n += 1
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                bad_json += 1
                continue
            blob = rec.get("transcription", "") + " ".join(
                i.get("description", "") for i in rec.get("expected_items", []))
            if ORDER_REF_RE.search(blob):
                order_refs += 1
    r.add(bad_json == 0, f"pairs: valid JSONL ({n} pairs)", f"{bad_json} invalid lines")
    r.add(order_refs == 0, "pairs: no order references left", f"{order_refs} leftovers")


def iter_text_files(root: Path):
    skip = {".git", "node_modules", ".venv", "venv", "__pycache__", ".tmp"}
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in TEXT_EXT and not (skip & set(p.parts)):
            yield p


def check_secrets_and_emails(paths, r: Report, label: str) -> None:
    sec_hits: list[str] = []
    email_hits: list[str] = []
    for p in paths:
        body = p.read_text(encoding="utf-8", errors="replace")
        for pat, name in SECRET_PATTERNS:
            if pat.search(body):
                sec_hits.append(f"{p.name}:{name}")
        for m in EMAIL_RE.findall(body):
            # author's own addresses and RFC-style fictional domains are allowed
            if not m.endswith(("biartechnology.com", "mikelju@gmail.com", "ejemplo.com")):
                email_hits.append(f"{p.name}:{m}")
    r.add(not sec_hits, f"{label}: no secrets", "; ".join(sorted(set(sec_hits))[:5]))
    r.add(not email_hits, f"{label}: no unexpected emails", "; ".join(sorted(set(email_hits))[:5]))


def check_phones(paths, r: Report) -> None:
    """Real admin rows embedded Spanish phone numbers - none may survive."""
    hits: list[str] = []
    for p in paths:
        body = p.read_text(encoding="utf-8", errors="replace")
        for m in PHONE_RE.findall(body):
            hits.append(f"{p.name}:{m[:3]}******")
    r.add(not hits, "data: no phone numbers", "; ".join(sorted(set(hits))[:5]))


def check_terms(terms_file: Path, roots: list[Path], r: Report) -> None:
    terms = [t for t in terms_file.read_text(encoding="utf-8").splitlines() if t.strip()]
    allv: set[str] = set()
    for t in terms:
        allv |= variants(t)
    hits: list[str] = []
    n_files = 0
    for root in roots:
        for p in iter_text_files(root):
            n_files += 1
            body = p.read_text(encoding="utf-8", errors="replace")
            for v in allv:
                if v in body:
                    hits.append(f"{p}:'{v}'")
    r.add(not hits, f"real-terms sweep ({len(terms)} terms, {len(allv)} variants, "
          f"{n_files} files)", "; ".join(sorted(set(hits))[:6]))


def main() -> None:
    ap = argparse.ArgumentParser(description="Anonymization gate")
    ap.add_argument("data_dir", nargs="?", default="data")
    ap.add_argument("--terms", help="real-terms list (file OUTSIDE the repo)")
    ap.add_argument("--repo", help="repo root for the full sweep (secrets/terms)")
    args = ap.parse_args()

    data = Path(args.data_dir)
    r = Report()
    print(f"Verifying anonymization of {data}\n")

    catalog_ids = check_catalog(data / "catalog.csv", r)
    check_historical(data / "historical.csv", catalog_ids, r)
    check_pairs(data / "extraction_pairs.jsonl", r)
    check_secrets_and_emails(iter_text_files(data), r, "data")
    check_phones(iter_text_files(data), r)

    roots = [data]
    if args.repo:
        repo = Path(args.repo)
        check_secrets_and_emails(iter_text_files(repo), r, "repo")
        roots = [repo]
    if args.terms:
        check_terms(Path(args.terms), roots, r)
    else:
        r.add(True, "real-terms sweep skipped",
              "run with --terms <external file> before publishing")

    print()
    r.dump_and_exit()


if __name__ == "__main__":
    main()
