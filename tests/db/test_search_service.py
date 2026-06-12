# tests/db/test_search_service.py
"""search_articles_service against the local DB: memory-first, dedupe, deterministic
demo ranking, per-article failure isolation. Spec US-2."""
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


def unit_vec(hot):
    v = [0.0] * DIM
    v[hot] = 1.0
    return v


def vec_lit(v):
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
    """3 catalog articles with near-parallel vectors (so catalog search returns several
    candidates) + a memory row pointing to article A."""
    async with pool.connection() as conn:
        rows = await (await conn.execute(
            "SELECT id_articulo, articulo FROM catalogo "
            "WHERE articulo <> '' ORDER BY id_articulo LIMIT 3")).fetchall()
        ids = [r[0] for r in rows]
        descs = [r[1] for r in rows]
        base = unit_vec(0)
        almost = [0.0] * DIM
        almost[0] = 0.9
        almost[1] = 0.43589   # ~0.9 cosine vs base
        third = [0.0] * DIM
        third[0] = 0.8
        third[2] = 0.6
        for art_id, vec in zip(ids, (base, almost, third)):
            await conn.execute(
                "INSERT INTO embeddings (id_articulo, embedding) "
                "VALUES (%s, %s::vector) "
                "ON CONFLICT (id_articulo) DO UPDATE SET embedding = EXCLUDED.embedding",
                (art_id, vec_lit(vec)))
        hist_id = (await (await conn.execute(
            "INSERT INTO historico_pedidos (user_text, catalog_description, "
            "id_articulo_catalogo, frequency, last_used_month) "
            "VALUES ('texto dictado memoria svc', %s, %s, 3, '2026-06') RETURNING id",
            (descs[0], ids[0]))).fetchone())[0]
        await conn.execute(
            "INSERT INTO historico_embeddings (historico_id, embedding) "
            "VALUES (%s, %s::vector)", (hist_id, vec_lit(base)))
    yield {"ids": ids, "descs": descs, "hist_id": hist_id}
    async with pool.connection() as conn:
        await conn.execute("DELETE FROM historico_embeddings WHERE historico_id = %s",
                           (hist_id,))
        await conn.execute("DELETE FROM historico_pedidos WHERE id = %s", (hist_id,))
        await conn.execute("DELETE FROM embeddings WHERE id_articulo = ANY(%s)", (ids,))


class StubEmbedder:
    def __init__(self, mapping):
        self.mapping = mapping

    async def embed_query(self, text):
        return self.mapping.get(text)


def make_clients(pool, mapping):
    from src.backend.app.services.search_utils import PgVectorSearcher
    return {"pool": pool, "searcher": PgVectorSearcher(pool, StubEmbedder(mapping))}


async def test_memory_first_pinned_and_deduped(pool, seeded, monkeypatch):
    from src.backend.app.services import search_service as svc
    monkeypatch.setattr(svc.settings, "APP_MODE", "demo")
    clients = make_clients(pool, {
        "texto dictado memoria svc": unit_vec(0),   # memory query
        "descripcion catalogo svc": unit_vec(0),    # catalog query
    })
    rows = await svc.search_articles_service(
        clients, ["texto dictado memoria svc"], ["descripcion catalogo svc"],
        num_opciones_busqueda=5, historical_threshold=0.75, catalog_threshold=0.5)
    assert rows, "expected candidates"
    # demo deterministic ranking: the memory hit leads
    assert rows[0]["Historical_match"] is True
    assert rows[0]["Ids"] == seeded["ids"][0]
    assert rows[0]["Date_score"] == 1
    # dedupe: the pinned description never reappears as a catalog row
    catalog_rows = [r for r in rows if not r["Historical_match"]]
    assert all(r["Description"] != rows[0]["Description"] for r in catalog_rows)
    assert catalog_rows, "catalog candidates expected besides the memory hit"
    # catalog rows sorted by Score desc (deterministic fallback)
    scores = [r["Score"] for r in catalog_rows]
    assert scores == sorted(scores, reverse=True)


async def test_below_threshold_memory_not_pinned(pool, seeded, monkeypatch):
    from src.backend.app.services import search_service as svc
    monkeypatch.setattr(svc.settings, "APP_MODE", "demo")
    weak = [0.0] * DIM
    weak[0] = 0.5
    weak[3] = 0.866   # cosine vs base = 0.5 < 0.75
    clients = make_clients(pool, {"q-debil": weak, "desc": unit_vec(0)})
    rows = await svc.search_articles_service(clients, ["q-debil"], ["desc"],
                                             num_opciones_busqueda=5)
    assert all(not r["Historical_match"] for r in rows)


async def test_failing_article_does_not_kill_the_order(pool, seeded, monkeypatch):
    from src.backend.app.services import search_service as svc
    monkeypatch.setattr(svc.settings, "APP_MODE", "demo")
    clients = make_clients(pool, {"buena": unit_vec(0), "desc-buena": unit_vec(0)})

    original = svc._search_single_article_async

    async def exploding(idx, article_text, *args, **kwargs):
        if article_text == "rota":
            raise RuntimeError("boom")
        return await original(idx, article_text, *args, **kwargs)

    monkeypatch.setattr(svc, "_search_single_article_async", exploding)
    rows = await svc.search_articles_service(
        clients, ["rota", "buena"], ["desc-rota", "desc-buena"],
        num_opciones_busqueda=3)
    assert rows, "the healthy article must survive"
    assert all(r["Article"] == "buena" for r in rows)


async def test_real_mode_reranks_with_llm_order(pool, seeded, monkeypatch):
    from src.backend.app.services import search_service as svc
    monkeypatch.setattr(svc.settings, "APP_MODE", "real")
    clients = make_clients(pool, {"q": unit_vec(0), "d": unit_vec(0)})

    def fake_rerank(payload_json):
        import json as _json
        ids = list(_json.loads(payload_json).keys())
        return _json.dumps({"ordered_ids": list(reversed(ids))})

    monkeypatch.setattr(svc, "_call_llm_for_reranking_sync", fake_rerank)
    rows = await svc.search_articles_service(clients, ["q"], ["d"],
                                             num_opciones_busqueda=3)
    assert rows
    # reversed order: the LLM put the last candidate first -> not the memory hit
    assert rows[0]["Historical_match"] is False


async def test_real_mode_llm_failure_falls_back_deterministic(pool, seeded, monkeypatch):
    from src.backend.app.services import search_service as svc
    monkeypatch.setattr(svc.settings, "APP_MODE", "real")
    clients = make_clients(pool, {"q": unit_vec(0), "d": unit_vec(0)})
    monkeypatch.setattr(svc, "_call_llm_for_reranking_sync", lambda payload: None)
    rows = await svc.search_articles_service(clients, ["q"], ["d"],
                                             num_opciones_busqueda=3)
    assert rows
    assert rows[0]["Historical_match"] is True   # fallback puts memory first
