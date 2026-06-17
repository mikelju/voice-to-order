# tests/realmode/test_real_e2e.py
"""Opt-in live E2E for real mode (Phase 6). SKIPPED unless RUN_REAL_MODE_TESTS=1.

Spends paid API quota (OpenAI embeddings + Gemini extraction/re-rank), so it is gated
and never runs in the default suite or in CI. The demo suite stays green and untouched.

Live stages covered here are text-only (no TTS, no Whisper):
  - extraction      -> Gemini (PROCESSING_LLM_MODEL), JSON mode + retry x3
  - query embedding -> text-embedding-3-small, reduced dim 256 (Phase-2 vector contract)
  - vector search   -> real HNSW search against the local catalog/memory
  - re-rank         -> Gemini (RANKING_LLM_MODEL) with the deterministic fallback

The Whisper transcription leg is exercised by the manual process-audio run recorded in
6.1_real_run_evidence.md (synthetic TTS audio), not here.

Wiring note: the test builds the real-mode services directly instead of driving the ASGI
app, because the app's lifespan resolves APP_MODE (and the demo replay store / embedder
mode) once at startup -- monkeypatching settings afterwards would not flip a demo-baked
app to real. Building EmbeddingService(mode="real") + PgVectorSearcher by hand exercises
the exact same production code paths (llm_wrapper, services, searcher) under real mode.

Requires the local DB (docker-compose up -d) and OPENAI_API_KEY + GOOGLE_API_KEY in .env.
"""
import os

import pytest
import pytest_asyncio

if os.environ.get("RUN_REAL_MODE_TESTS") != "1":
    pytest.skip("real-mode E2E is opt-in (set RUN_REAL_MODE_TESTS=1; spends API quota)",
                allow_module_level=True)

pytest.importorskip("psycopg")
from tests.backend.conftest import db_reachable  # noqa: E402

# A fictional dictated order: no real client, site, or part numbers. The order number is
# deliberately fictional and not resolvable by the simulated ERP. Items are generic
# fluid-handling accessories expected to have catalog matches.
DICTATED_ORDER = (
    "Pedido 90001. Dos codos de media inox 304 noventa grados. "
    "Tres valvulas de bola de media de laton. "
    "Una junta de goma de una pulgada. "
    "Cinco metros de tubo DN20 inox."
)


@pytest_asyncio.fixture
async def real_clients(monkeypatch):
    if not db_reachable():
        pytest.skip("local DB not reachable (docker-compose up -d to run these tests)")

    from src.backend.app.core.config import settings
    if not settings.OPENAI_API_KEY or not settings.GOOGLE_API_KEY:
        pytest.skip("real mode needs OPENAI_API_KEY and GOOGLE_API_KEY in .env")

    from src.backend.app.core.db import create_pool
    from src.backend.app.services.embedding_service import EmbeddingService
    from src.backend.app.services.search_utils import PgVectorSearcher

    # Activate real mode for every service that reads settings.APP_MODE at call time.
    monkeypatch.setattr(settings, "APP_MODE", "real")

    pool = create_pool()
    await pool.open()
    try:
        embedder = EmbeddingService(pool, mode="real")
        searcher = PgVectorSearcher(pool, embedder)
        yield {"pool": pool, "embedder": embedder, "searcher": searcher}
    finally:
        await pool.close()


async def test_live_query_embedding_dimension(real_clients):
    """text-embedding-3-small returns the reduced 256-dim vector (Phase-2 schema contract)."""
    from src.backend.app.core.config import settings

    vec = await real_clients["embedder"].embed_query(
        "valvula de bola de media de laton")
    assert vec is not None, "live embedding returned None (check OPENAI_API_KEY / quota)"
    assert len(vec) == settings.EMBEDDINGS_DIM == 256


async def test_live_extraction_and_search(real_clients):
    """Gemini extraction -> live-embedding HNSW search -> Gemini re-rank (fallback safe)."""
    from src.backend.app.services.order_processing_service import (
        process_order_text_service)
    from src.backend.app.services.search_service import search_articles_service

    extracted = await process_order_text_service(real_clients, DICTATED_ORDER)
    assert extracted is not None, "live extraction returned None (Gemini failure?)"

    articles = extracted["articles_list"]
    descriptions = extracted["description_list_for_search"]
    assert articles, "extraction produced no article lines"
    assert len(articles) == len(descriptions)
    # the dictated order number survived extraction
    assert "90001" in str(extracted["num_order"])

    candidates = await search_articles_service(
        real_clients, articles, descriptions, num_opciones_busqueda=5)
    assert candidates, "live vector search produced no candidates against the catalog"

    # every candidate is a real catalog row with a similarity score in [0, 1]; the
    # searcher already filtered below the catalog threshold (0.5) server-side, so any
    # candidate at all proves the live-embedding HNSW path returned real hits.
    for row in candidates:
        assert row["Description"], "candidate without a catalog description"
        assert 0.0 <= float(row["Score"]) <= 1.0
