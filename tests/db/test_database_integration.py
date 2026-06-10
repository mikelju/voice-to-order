# tests/db/test_database_integration.py
"""Integration tests against the local Postgres (docker-compose).

They SKIP cleanly when the DB is unreachable, so CI without Docker stays green.
With the DB up and data loaded they prove: counts, FKs, the ported functions, the
HNSW indexes and the trigram fallback.
"""
import csv
import os
from pathlib import Path

import pytest

psycopg = pytest.importorskip("psycopg")

URL = os.environ.get("DATABASE_URL", "postgresql://vto:vto@localhost:5433/vto")
DATA = Path(__file__).resolve().parents[2] / "data"


@pytest.fixture(scope="module")
def conn():
    try:
        c = psycopg.connect(URL, connect_timeout=3)
    except psycopg.OperationalError:
        pytest.skip("local DB not reachable (docker-compose up -d to run these tests)")
    yield c
    c.close()


def q1(conn, sql, *params):
    with conn.cursor() as cur:
        cur.execute(sql, params or None)
        return cur.fetchone()[0]


def test_counts_match_dataset(conn):
    with open(DATA / "catalog.csv", encoding="utf-8") as f:
        n_cat = sum(1 for _ in csv.DictReader(f))
    with open(DATA / "historical.csv", encoding="utf-8") as f:
        n_hist = sum(1 for _ in csv.DictReader(f))
    assert q1(conn, "SELECT count(*) FROM catalogo") == n_cat
    assert q1(conn, "SELECT count(*) FROM historico_pedidos") == n_hist


def test_referential_integrity(conn):
    orphans = q1(conn, """
        SELECT count(*) FROM historico_pedidos h
        LEFT JOIN catalogo c ON h.id_articulo_catalogo = c.id_articulo
        WHERE h.id_articulo_catalogo IS NOT NULL AND c.id_articulo IS NULL""")
    assert orphans == 0


def test_ported_functions_exist_and_run(conn):
    for fn in ("buscar_articulos", "buscar_historicos"):
        assert q1(conn, "SELECT count(*) FROM pg_proc WHERE proname = %s", fn) == 1
    # run with a zero vector: must execute (empty result while embeddings are unloaded is fine)
    zero = "[" + ",".join(["0"] * 256) + "]"
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM buscar_articulos(%s::vector, 0.5, 5)", (zero,))
        cur.fetchall()
        cur.execute("SELECT * FROM buscar_historicos(%s::vector, 0.75, 1)", (zero,))
        cur.fetchall()


def test_hnsw_indexes_exist(conn):
    for idx in ("embeddings_embedding_idx", "historico_embeddings_embedding_idx"):
        assert q1(conn, "SELECT count(*) FROM pg_indexes WHERE indexname = %s", idx) == 1


def test_trigram_fallback_search(conn):
    hits = q1(conn, "SELECT count(*) FROM catalogo WHERE articulo ILIKE %s", "%VALVULA%")
    assert hits > 0
