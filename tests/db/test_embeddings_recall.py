# tests/db/test_embeddings_recall.py
"""Phase-4 recall: with the real committed embeddings loaded, memory rows find
themselves at rank 1 and demo queries with an exact catalog twin rank it first.
Skips cleanly when the embeddings are not loaded."""
import os
import sys
from pathlib import Path

import pytest

psycopg = pytest.importorskip("psycopg")

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

URL = os.environ.get("DATABASE_URL", "postgresql://vto:vto@localhost:5433/vto")
DATA = Path(__file__).resolve().parents[2] / "data"


@pytest.fixture(scope="module")
def conn():
    try:
        c = psycopg.connect(URL, connect_timeout=3)
    except psycopg.OperationalError:
        pytest.skip("local DB not reachable")
    n = c.execute("SELECT count(*) FROM embeddings").fetchone()[0]
    if n == 0:
        c.close()
        pytest.skip("embeddings not loaded (run tools/generate_embeddings.py + load)")
    yield c
    c.close()


def vec_lit(vec):
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"


def test_memory_rows_recall_themselves(conn):
    from emblib import read_embeddings
    ids, vecs = read_embeddings(DATA / "embeddings" / "historical")
    for text, vec in list(zip(ids, vecs))[::199][:5]:
        row = conn.execute(
            "SELECT user_text, similarity FROM buscar_historicos(%s::vector, 0.5, 1)",
            (vec_lit(vec),)).fetchone()
        assert row is not None and row[0] == text, f"memory recall failed for {text!r}"
        assert row[1] > 0.999


def test_demo_queries_rank_their_catalog_twin_first(conn):
    from emblib import read_embeddings
    ids, vecs = read_embeddings(DATA / "embeddings" / "queries")
    checked = 0
    for text, vec in zip(ids, vecs):
        twin = conn.execute(
            "SELECT 1 FROM catalogo WHERE articulo = %s AND is_active", (text,)).fetchone()
        if not twin:
            continue
        top = conn.execute(
            "SELECT articulo FROM buscar_articulos(%s::vector, 0.5, 1)",
            (vec_lit(vec),)).fetchone()
        assert top is not None and top[0] == text, f"catalog recall failed for {text!r}"
        checked += 1
        if checked >= 5:
            break
    assert checked > 0, "no demo query had an exact catalog twin (unexpected)"
