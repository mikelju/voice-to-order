# tools/apply_sql.py
"""Apply db/init/*.sql to a LIVE database (docker-entrypoint only runs them on first boot).

Usage:
    python tools/apply_sql.py                 # applies the re-applicable scripts (02+)
    python tools/apply_sql.py db/init/03_phase3.sql

Env:
    DATABASE_URL  (default: postgresql://vto:vto@localhost:5433/vto)

01_schema.sql is first-boot only (plain CREATE TABLE); 02+ are idempotent by design and
are what the default mode applies. Pass explicit paths to override.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    import psycopg
except ImportError:
    print("[ERROR] psycopg not installed: pip install -r requirements.txt")
    sys.exit(2)

DEFAULT_URL = "postgresql://vto:vto@localhost:5433/vto"


def main() -> None:
    targets = [Path(a) for a in sys.argv[1:]] or [
        p for p in sorted(Path("db/init").glob("*.sql"))
        if not p.name.startswith("01_")]
    url = os.environ.get("DATABASE_URL", DEFAULT_URL)
    try:
        conn = psycopg.connect(url, connect_timeout=5)
    except psycopg.OperationalError as e:
        print(f"[ERROR] cannot connect to {url.split('@')[-1]}: {e}")
        print("        is the DB up? -> docker-compose -f db/docker-compose.yml up -d")
        sys.exit(2)
    with conn:
        for path in targets:
            sql = path.read_text(encoding="utf-8")
            conn.execute(sql)
            print(f"[OK] applied {path}")


if __name__ == "__main__":
    main()
