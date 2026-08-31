# tools/history_sweep.py
"""Real-terms sweep over the WHOLE git history, not just the working tree.

`verify_anonymization.py --terms` checks the files that exist now. This checks every
blob ever committed and every commit message, because a real term committed and later
deleted still leaks (CLAUDE.md, known gotcha #1) and a force-push does not remove it.

    python tools/history_sweep.py --terms <path-outside-the-repo>
    python tools/history_sweep.py --terms <file> --repo /path/to/repo

The terms list lives OUTSIDE the repo (it is the thing being protected), so this runs on
the author's machine, not in CI. Exit code 0 = CLEAN, 1 = at least one hit.

Output never prints a matched term: it reports where and how many, so the report itself
can be pasted anywhere. Writing the leaked term into a file is how fix-2 happened.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import unicodedata
from pathlib import Path

TEXT_EXT = (".csv", ".jsonl", ".md", ".py", ".txt", ".sql", ".json", ".yml", ".yaml",
            ".ts", ".tsx", ".js", ".html", ".css", ".env")


def run(repo: Path, args: list[str]) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace").stdout


def variants(term: str) -> set[str]:
    """Case and separator variants of one term (same rules as verify_anonymization)."""
    t = term.strip()
    if not t:
        return set()
    deacc = "".join(c for c in unicodedata.normalize("NFKD", t)
                    if not unicodedata.combining(c))
    out: set[str] = set()
    for b in {t, t.lower(), t.upper(), t.title(), deacc, deacc.lower()}:
        out |= {b, b.replace(" ", "_"), b.replace(" ", "-"), b.replace(" ", "")}
    return {v for v in out if len(v) >= 3}


def sweep(repo: Path, terms: list[str]) -> tuple[dict[str, int], dict[str, int], int, int]:
    """Return (blob hits by path, message hits by commit, n_blobs, n_variants).

    Hit values are variant counts, NOT term counts: one term can match several
    variants of itself (this label is what made fix-2's inventory read as two
    distinct names when there was one).
    """
    by_variant = {v: t for t in terms for v in variants(t)}
    all_variants = set(by_variant)

    blobs = []
    for line in run(repo, ["rev-list", "--all", "--objects"]).splitlines():
        parts = line.split(" ", 1)
        if len(parts) == 2 and parts[1].lower().endswith(TEXT_EXT):
            blobs.append((parts[0], parts[1]))

    blob_hits: dict[str, int] = {}
    for sha, path in blobs:
        content = run(repo, ["cat-file", "-p", sha])
        found = {v for v in all_variants if v in content}
        if found:
            blob_hits[path] = max(blob_hits.get(path, 0), len(found))

    msg_hits: dict[str, int] = {}
    for sha in run(repo, ["rev-list", "--all"]).split():
        message = run(repo, ["log", "-1", "--format=%B", sha])
        found = {v for v in all_variants if v in message}
        if found:
            msg_hits[sha[:7]] = len(found)

    return blob_hits, msg_hits, len(blobs), len(all_variants)


def main() -> None:
    ap = argparse.ArgumentParser(description="Real-terms sweep over the git history")
    ap.add_argument("--terms", required=True,
                    help="real-terms list, one per line (file OUTSIDE the repo)")
    ap.add_argument("--repo", default=".", help="repo root (default: current directory)")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    terms = [t.strip() for t in Path(args.terms).read_text(encoding="utf-8").splitlines()
             if t.strip()]
    blob_hits, msg_hits, n_blobs, n_variants = sweep(repo, terms)

    print(f"[*] {len(terms)} terms -> {n_variants} variants")
    print(f"[*] scanning {n_blobs} text blobs and every commit message in {repo.name}")

    if not blob_hits and not msg_hits:
        print("[OK] git-history sweep CLEAN: no real term in any blob or commit message")
        sys.exit(0)

    print(f"[FAIL] real terms in history: {len(blob_hits)} path(s), "
          f"{len(msg_hits)} commit message(s)")
    for path, n in sorted(blob_hits.items()):
        print(f"   blob    {path}: {n} variant(s) matched")
    for sha, n in sorted(msg_hits.items()):
        print(f"   message {sha}: {n} variant(s) matched")
    print("   (terms are never printed - look them up in your external list)")
    sys.exit(1)


if __name__ == "__main__":
    main()
