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


def load(conn: psycopg.Connection, data: Path) -> None:
    with conn.cursor() as cur:
        cur.execute("TRUNCATE historico_embeddings, historico_pedidos, embeddings, catalogo")

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
        for table in ("catalogo", "historico_pedidos", "embeddings", "historico_embeddings"):
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
        for table, n in counts(conn).items():
            print(f"[OK] {table}: {n} rows")


if __name__ == "__main__":
    main()
