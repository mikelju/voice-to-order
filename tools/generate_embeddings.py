# tools/generate_embeddings.py
"""One-off generation of the versioned embeddings (author's machine, needs OPENAI_API_KEY).

Usage:
    python tools/generate_embeddings.py              # generate data/embeddings/*
    python tools/generate_embeddings.py --verify     # recall checks against the local DB

Embeds with text-embedding-3-small at dimension 256 (Phase-2 schema contract):
- catalog:    data/catalog.csv  ->  data/embeddings/catalog.{ids.txt,f32}   (key: id_articulo)
- historical: data/historical.csv -> data/embeddings/historical.{ids.txt,f32} (key: row index,
              text embedded: user_text — ids file stores "idx<TAB>user_text" is NOT used;
              keys are the user_text strings, order = file order)
- queries:    unique expected_items[].description from data/extraction_pairs.jsonl ->
              data/embeddings/queries.{ids.txt,f32} (key: the exact query text)

Batched (1000 inputs/request) with retry x3 backoff 2s*attempt.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emblib import DIM, read_embeddings, write_embeddings  # noqa: E402

MODEL = os.environ.get("EMBEDDINGS_MODEL_NAME", "text-embedding-3-small")
BATCH = 1000
MAX_RETRIES = 3
DEFAULT_URL = "postgresql://vto:vto@localhost:5433/vto"


def embed_batched(client, texts: list[str]) -> list[list[float]]:
    out: list[list[float]] = []
    for start in range(0, len(texts), BATCH):
        batch = texts[start:start + BATCH]
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = client.embeddings.create(model=MODEL, input=batch,
                                                dimensions=DIM)
                out.extend(d.embedding for d in resp.data)
                break
            except Exception as exc:
                if attempt == MAX_RETRIES:
                    raise
                delay = 2 * attempt
                print(f"[WARN] batch {start // BATCH} failed ({exc}); "
                      f"retry in {delay}s ({attempt}/{MAX_RETRIES})")
                time.sleep(delay)
        done = min(start + BATCH, len(texts))
        print(f"[OK] embedded {done}/{len(texts)}")
    return out


def load_sources(data: Path) -> dict[str, tuple[list[str], list[str]]]:
    """Return {dataset: (keys, texts_to_embed)}."""
    cat_keys: list[str] = []
    cat_texts: list[str] = []
    with open(data / "catalog.csv", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            desc = " ".join((row["articulo"] or "").split())
            if desc:
                cat_keys.append(row["id_articulo"])
                cat_texts.append(desc)

    hist_keys: list[str] = []
    with open(data / "historical.csv", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            text = (row["user_text"] or "").strip()
            if text:
                hist_keys.append(text)
    hist_keys = list(dict.fromkeys(hist_keys))   # dedupe, keep order

    queries: list[str] = []
    seen: set[str] = set()
    with open(data / "extraction_pairs.jsonl", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            for item in json.loads(line)["expected_items"]:
                q = item["description"].strip()
                if q and q not in seen:
                    seen.add(q)
                    queries.append(q)

    return {"catalog": (cat_keys, cat_texts),
            "historical": (hist_keys, hist_keys),
            "queries": (queries, queries)}


def generate(data: Path) -> None:
    from openai import OpenAI
    if not os.environ.get("OPENAI_API_KEY"):
        print("[ERROR] OPENAI_API_KEY is required for generation")
        sys.exit(2)
    client = OpenAI()
    out_dir = data / "embeddings"
    for name, (keys, texts) in load_sources(data).items():
        print(f"-- {name}: {len(keys)} texts")
        vectors = embed_batched(client, texts)
        write_embeddings(out_dir / name, keys, vectors)
        print(f"[OK] wrote {out_dir / name}.f32")


def verify(data: Path) -> None:
    """Recall checks against the local DB (run after load_database.py)."""
    import psycopg
    url = os.environ.get("DATABASE_URL", DEFAULT_URL)
    conn = psycopg.connect(url, connect_timeout=5)
    failures = 0

    hist_ids, hist_vecs = read_embeddings(data / "embeddings" / "historical")
    sample = list(zip(hist_ids, hist_vecs))[::97][:10]   # spread sample
    with conn:
        for text, vec in sample:
            lit = "[" + ",".join(repr(x) for x in vec) + "]"
            row = conn.execute(
                "SELECT user_text, similarity FROM buscar_historicos(%s::vector, 0.5, 1)",
                (lit,)).fetchone()
            if not row or row[0] != text or row[1] < 0.999:
                print(f"[ERROR] memory recall failed for: {text[:50]!r} -> {row}")
                failures += 1
        q_ids, q_vecs = read_embeddings(data / "embeddings" / "queries")
        checked = 0
        for text, vec in zip(q_ids, q_vecs):
            exact = conn.execute(
                "SELECT id_articulo FROM catalogo WHERE articulo = %s AND is_active",
                (text,)).fetchone()
            if not exact:
                continue   # demo query without an exact catalog twin
            lit = "[" + ",".join(repr(x) for x in vec) + "]"
            top = conn.execute(
                "SELECT articulo FROM buscar_articulos(%s::vector, 0.5, 1)",
                (lit,)).fetchone()
            if not top or top[0] != text:
                print(f"[ERROR] catalog recall failed for: {text[:50]!r} -> {top}")
                failures += 1
            checked += 1
            if checked >= 10:
                break
    print(f"[{'OK' if not failures else 'ERROR'}] recall verification: "
          f"{10 + checked - failures}/{10 + checked} checks passed")
    sys.exit(1 if failures else 0)


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate/verify precomputed embeddings")
    ap.add_argument("--data", default="data")
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()
    data = Path(args.data)
    if args.verify:
        verify(data)
    else:
        generate(data)


if __name__ == "__main__":
    main()
