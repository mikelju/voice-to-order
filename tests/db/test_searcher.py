# tests/db/test_searcher.py
"""PgVectorSearcher against the local DB with SYNTHETIC vectors (Phase 4 brings the real
ones). Proves: the ported functions are called correctly, the demo query-embedding store
works, and the trigram fallback answers when no vector exists. Spec US-2."""
import asyncio
import os
import sys

import pytest
import pytest_asyncio

psycopg = pytest.importorskip("psycopg")
from psycopg_pool import AsyncConnectionPool  # noqa: E402

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

URL = os.environ.get("DATABASE_URL", "postgresql://vto:vto@localhost:5433/vto")
DIM = 256


def unit_vec(hot: int) -> list[float]:
    v = [0.0] * DIM
    v[hot] = 1.0
    return v


def vec_lit(v: list[float]) -> str:
    return "[" + ",".join(repr(float(x)) for x in v) + "]"


@pytest_asyncio.fixture
async def pool():
    try:
        with psycopg.connect(URL, connect_timeout=3):
            pass
    except psycopg.OperationalError:
        pytest.skip("local DB not reachable (docker-compose up -d to run these tests)")
    p = AsyncConnectionPool(URL, min_size=1, max_size=4, open=False)
    await p.open()
    yield p
    await p.close()


@pytest_asyncio.fixture
async def seeded(pool):
    """Two catalog articles + one memory row with synthetic orthogonal embeddings, plus
    a precomputed demo query vector. Cleaned up afterwards."""
    async with pool.connection() as conn:
        rows = await (await conn.execute(
            "SELECT id_articulo, articulo FROM catalogo "
            "WHERE articulo <> '' ORDER BY id_articulo LIMIT 2")).fetchall()
        (id_a, desc_a), (id_b, _desc_b) = rows
        await conn.execute(
            "INSERT INTO embeddings (id_articulo, embedding) VALUES (%s, %s::vector) "
            "ON CONFLICT (id_articulo) DO UPDATE SET embedding = EXCLUDED.embedding",
            (id_a, vec_lit(unit_vec(0))))
        await conn.execute(
            "INSERT INTO embeddings (id_articulo, embedding) VALUES (%s, %s::vector) "
            "ON CONFLICT (id_articulo) DO UPDATE SET embedding = EXCLUDED.embedding",
            (id_b, vec_lit(unit_vec(1))))
        hist_id = (await (await conn.execute(
            "INSERT INTO historico_pedidos (user_text, catalog_description, "
            "id_articulo_catalogo, frequency, last_used_month) "
            "VALUES ('frase de prueba searcher', %s, %s, 1, '2026-06') RETURNING id",
            (desc_a, id_a))).fetchone())[0]
        await conn.execute(
            "INSERT INTO historico_embeddings (historico_id, embedding) "
            "VALUES (%s, %s::vector)", (hist_id, vec_lit(unit_vec(0))))
        await conn.execute(
            "INSERT INTO query_embeddings (query_text, embedding) "
            "VALUES ('query precomputada de prueba', %s::vector) "
            "ON CONFLICT (query_text) DO UPDATE SET embedding = EXCLUDED.embedding",
            (vec_lit(unit_vec(0)),))
    yield {"id_a": id_a, "desc_a": desc_a, "id_b": id_b, "hist_id": hist_id}
    async with pool.connection() as conn:
        await conn.execute("DELETE FROM historico_embeddings WHERE historico_id = %s",
                           (hist_id,))
        await conn.execute("DELETE FROM historico_pedidos WHERE id = %s", (hist_id,))
        await conn.execute("DELETE FROM embeddings WHERE id_articulo IN (%s, %s)",
                           (id_a, id_b))
        await conn.execute("DELETE FROM query_embeddings "
                           "WHERE query_text = 'query precomputada de prueba'")


class StubEmbedder:
    """Returns a fixed vector for known queries, None otherwise (forces trigram)."""
    def __init__(self, mapping):
        self.mapping = mapping

    async def embed_query(self, text):
        return self.mapping.get(text)


async def test_vector_catalog_search_hits_seeded_article(pool, seeded):
    from src.backend.app.services.search_utils import PgVectorSearcher
    searcher = PgVectorSearcher(pool, StubEmbedder({"q": unit_vec(0)}))
    out = await searcher.search_catalog("q", threshold=0.5, count=5)
    assert out and out[0]["id_articulo"] == seeded["id_a"]
    assert out[0]["similarity"] == pytest.approx(1.0, abs=1e-6)


async def test_vector_historical_search_returns_link(pool, seeded):
    from src.backend.app.services.search_utils import PgVectorSearcher
    searcher = PgVectorSearcher(pool, StubEmbedder({"q": unit_vec(0)}))
    out = await searcher.search_historical("q", threshold=0.7, count=1)
    assert out and out[0]["id_articulo_catalogo"] == seeded["id_a"]
    assert out[0]["user_text"] == "frase de prueba searcher"


async def test_demo_store_lookup_via_embedding_service(pool, seeded):
    from src.backend.app.services.embedding_service import EmbeddingService
    emb = EmbeddingService(pool, mode="demo")
    vec = await emb.embed_query("query precomputada de prueba")
    assert vec is not None and len(vec) == DIM and vec[0] == 1.0
    assert await emb.embed_query("query inexistente") is None


async def test_trigram_fallback_when_no_vector(pool, seeded):
    from src.backend.app.services.search_utils import PgVectorSearcher
    searcher = PgVectorSearcher(pool, StubEmbedder({}))   # no vectors at all
    out = await searcher.search_catalog(seeded["desc_a"], threshold=0.5, count=5)
    assert out, "trigram fallback must answer"
    assert any(r["id_articulo"] == seeded["id_a"] for r in out)


async def test_get_catalog_item_details_live_description(pool, seeded):
    from src.backend.app.services.search_utils import PgVectorSearcher
    searcher = PgVectorSearcher(pool, StubEmbedder({}))
    details = await searcher.get_catalog_item_details(seeded["id_a"])
    assert details["articulo"] == seeded["desc_a"]
    assert await searcher.get_catalog_item_details("ART-noexiste00") is None


async def test_warmup_does_not_raise(pool, seeded):
    from src.backend.app.services.search_utils import PgVectorSearcher
    searcher = PgVectorSearcher(pool, StubEmbedder({}))
    await searcher.warmup()
