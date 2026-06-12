# src/backend/app/services/embedding_service.py
"""Query-embedding provider.

demo mode: looks the query up in the precomputed `query_embeddings` table (filled by
Phase 4). Returns None when absent — the searcher then falls back to pg_trgm so demo
never needs a network call.

real mode: text-embedding-3-small with the reduced dimension (256) of the Phase-2 schema,
called through the async OpenAI client (the original embedded synchronously inside async
code and blocked the event loop — fixed consciously, see the phase plan).
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from ..core.config import settings

logger = logging.getLogger(__name__)

_async_openai: Any = None


def _client() -> Any:
    global _async_openai
    if _async_openai is None:
        from openai import AsyncOpenAI
        _async_openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _async_openai


class EmbeddingService:
    def __init__(self, pool: Any, mode: Optional[str] = None):
        self._pool = pool
        self._mode = mode or settings.APP_MODE

    async def embed_query(self, text: str) -> Optional[list[float]]:
        if self._mode == "demo":
            return await self._lookup(text)
        return await self._embed_live(text)

    async def embed_documents(self, texts: list[str]) -> Optional[list[list[float]]]:
        """Real mode only (new-memory embeddings). Demo returns None (trigram reach)."""
        if self._mode == "demo":
            return None
        try:
            resp = await _client().embeddings.create(
                model=settings.EMBEDDINGS_MODEL_NAME, input=texts,
                dimensions=settings.EMBEDDINGS_DIM)
            return [d.embedding for d in resp.data]
        except Exception:
            logger.exception("embed_documents failed")
            return None

    async def _embed_live(self, text: str) -> Optional[list[float]]:
        try:
            resp = await _client().embeddings.create(
                model=settings.EMBEDDINGS_MODEL_NAME, input=[text],
                dimensions=settings.EMBEDDINGS_DIM)
            return resp.data[0].embedding
        except Exception:
            logger.exception("embed_query failed (live)")
            return None

    async def _lookup(self, text: str) -> Optional[list[float]]:
        try:
            async with self._pool.connection() as conn:
                cur = await conn.execute(
                    "SELECT embedding::text FROM query_embeddings WHERE query_text = %s",
                    (text,))
                row = await cur.fetchone()
            if not row:
                return None
            return [float(x) for x in row[0].strip("[]").split(",")]
        except Exception:
            logger.exception("query_embeddings lookup failed")
            return None
