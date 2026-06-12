# tools/load_database.py
"""Load data/ (anonymized dataset) into the local Postgres.

Usage:
    python tools/load_database.py [--data data] [--check]

Env:
    DATABASE_URL  (default: postgresql://vto:vto@localhost:5433/vto)

Idempotent: runs in one transaction, truncates and reloads. --check only reports counts.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

try:
    import psycopg
except ImportError:
    print("[ERROR] psycopg not installed: pip install -r requirements.txt")
    sys.exit(2)

DEFAULT_URL = "postgresql://vto:vto@localhost:5433/vto"


def month_to_date(month: str) -> str | None:
    return f"{month}-01" if month else None


def vec_lit(vec: list[float]) -> str:
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"


def load_embeddings(conn: psycopg.Connection, data: Path) -> None:
    """Load data/embeddings/ (Phase 4) when present; quiet skip otherwise."""
    emb_dir = data / "embeddings"
    if not (emb_dir / "catalog.f32").is_file():
        print("[OK] data/embeddings/ not present - skipping (Phase 4 generates it)")
        return
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from emblib import read_embeddings

    with conn.cursor() as cur:
        ids, vecs = read_embeddings(emb_dir / "catalog")
        with cur.copy("COPY embeddings (id_articulo, embedding) FROM STDIN") as copy:
            for art_id, vec in zip(ids, vecs):
                copy.write_row((art_id, vec_lit(vec)))

        texts, vecs = read_embeddings(emb_dir / "historical")
        by_text = dict(zip(texts, vecs))
        cur.execute("SELECT id, user_text FROM historico_pedidos")
        rows = cur.fetchall()
        with cur.copy("COPY historico_embeddings (historico_id, embedding) "
                      "FROM STDIN") as copy:
            for hist_id, user_text in rows:
                vec = by_text.get(user_text)
                if vec is not None:
                    copy.write_row((hist_id, vec_lit(vec)))

        queries, vecs = read_embeddings(emb_dir / "queries")
        with cur.copy("COPY query_embeddings (query_text, embedding) FROM STDIN") as copy:
            for query, vec in zip(queries, vecs):
                copy.write_row((query, vec_lit(vec)))


def load(conn: psycopg.Connection, data: Path) -> None:
    with conn.cursor() as cur:
        cur.execute("TRUNCATE query_embeddings, historico_embeddings, historico_pedidos, "
                    "embeddings, catalogo")

        with open(data / "catalog.csv", encoding="utf-8", newline="") as f, \
                cur.copy("COPY catalogo (id_articulo, articulo, fecha_ultima_compra) "
                         "FROM STDIN") as copy:
            for row in csv.DictReader(f):
                copy.write_row((row["id_articulo"], row["articulo"],
                                month_to_date(row["ultima_compra_mes"])))

        with open(data / "historical.csv", encoding="utf-8", newline="") as f, \
                cur.copy("COPY historico_pedidos (user_text, catalog_description, "
                         "id_articulo_catalogo, frequency, last_used_month) FROM STDIN") as copy:
            for row in csv.DictReader(f):
                copy.write_row((row["user_text"], row["catalog_description"],
                                row["id_articulo"], int(row["frequency"]),
                                row["last_used_month"]))


def counts(conn: psycopg.Connection) -> dict[str, int]:
    out = {}
    with conn.cursor() as cur:
        for table in ("catalogo", "historico_pedidos", "embeddings",
                      "historico_embeddings", "query_embeddings"):
            cur.execute(f"SELECT count(*) FROM {table}")  # fixed identifier set, not user input
            out[table] = cur.fetchone()[0]
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Load data/ into the local Postgres")
    ap.add_argument("--data", default="data")
    ap.add_argument("--check", action="store_true", help="report row counts only")
    args = ap.parse_args()

    url = os.environ.get("DATABASE_URL", DEFAULT_URL)
    try:
        conn = psycopg.connect(url, connect_timeout=5)
    except psycopg.OperationalError as e:
        print(f"[ERROR] cannot connect to {url.split('@')[-1]}: {e}")
        print("        is the DB up? -> docker-compose -f db/docker-compose.yml up -d")
        sys.exit(2)

    with conn:
        if not args.check:
            load(conn, Path(args.data))
            load_embeddings(conn, Path(args.data))
        for table, n in counts(conn).items():
            print(f"[OK] {table}: {n} rows")


if __name__ == "__main__":
    main()
