# src/backend/app/services/search_utils.py
"""PgVectorSearcher: access to the ported CTE/HNSW SQL functions, over the psycopg pool.

Ported from the original's PgVectorSearcher (Supabase RPC -> direct SELECT of the same
functions). The functions themselves are verbatim ports (db/init/02_functions.sql) — do
not "improve" them.

Demo addition: when the query has no embedding (no API key and not precomputed), the
catalog/historical searches fall back to pg_trgm similarity so the demo flow never errors.
The fallback is logged and the result rows carry the same keys as the vector path.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

CATALOG_TABLE = "catalogo"
CATALOG_ID_COL = "id_articulo"
CATALOG_DESC_COL = "articulo"

TRGM_SIM_THRESHOLD = 0.10   # demo fallback floor (pg_trgm similarity)


def _vec_literal(vec: list[float]) -> str:
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"


class PgVectorSearcher:
    def __init__(self, pool: Any, embedder: Any):
        self._pool = pool
        self._embedder = embedder

    # -- vector paths (ported) -------------------------------------------------

    async def search_catalog(self, query_text: str, threshold: float = 0.5,
                             count: int = 10) -> list[dict]:
        vec = await self._embedder.embed_query(query_text)
        if vec is None:
            return await self._search_catalog_trgm(query_text, count)
        try:
            async with self._pool.connection() as conn:
                cur = await conn.execute(
                    "SELECT id_articulo, articulo, fecha_ultima_compra, similarity "
                    "FROM buscar_articulos(%s::vector, %s, %s)",
                    (_vec_literal(vec), threshold, count))
                rows = await cur.fetchall()
            return [{"id_articulo": r[0], "articulo": r[1],
                     "fecha_ultima_compra": r[2].isoformat() if r[2] else None,
                     "similarity": float(r[3])} for r in rows]
        except Exception:
            logger.exception("buscar_articulos failed")
            return []

    async def search_historical(self, query_text: str, threshold: float = 0.7,
                                count: int = 5) -> list[dict]:
        vec = await self._embedder.embed_query(query_text)
        if vec is None:
            return await self._search_historical_trgm(query_text, count, threshold)
        try:
            async with self._pool.connection() as conn:
                cur = await conn.execute(
                    "SELECT id, user_text, catalog_description, similarity, "
                    "id_articulo_catalogo "
                    "FROM buscar_historicos(%s::vector, %s, %s)",
                    (_vec_literal(vec), threshold, count))
                rows = await cur.fetchall()
            return [{"id": r[0], "user_text": r[1], "catalog_description": r[2],
                     "similarity": float(r[3]), "id_articulo_catalogo": r[4]}
                    for r in rows]
        except Exception:
            logger.exception("buscar_historicos failed")
            return []

    async def get_catalog_item_details(self, id_articulo: str) -> Optional[dict]:
        try:
            async with self._pool.connection() as conn:
                cur = await conn.execute(
                    "SELECT id_articulo, articulo, fecha_ultima_compra FROM catalogo "
                    "WHERE id_articulo = %s AND is_active = TRUE LIMIT 1",
                    (id_articulo,))
                row = await cur.fetchone()
            if not row:
                return None
            return {"id_articulo": row[0], "articulo": row[1],
                    "fecha_ultima_compra": row[2].isoformat() if row[2] else None}
        except Exception:
            logger.exception("get_catalog_item_details failed")
            return None

    async def warmup(self) -> None:
        """Touch both HNSW indexes so they sit in shared_buffers (ported)."""
        try:
            zero = _vec_literal([0.0] * 256)
            async with self._pool.connection() as conn:
                await conn.execute(
                    "SELECT 1 FROM buscar_articulos(%s::vector, 0.99, 1)", (zero,))
                await conn.execute(
                    "SELECT 1 FROM buscar_historicos(%s::vector, 0.99, 1)", (zero,))
            logger.info("HNSW warmup done")
        except Exception:
            logger.warning("HNSW warmup failed (non-fatal)")

    # -- demo trigram fallbacks --------------------------------------------------

    async def _search_catalog_trgm(self, query_text: str, count: int) -> list[dict]:
        logger.info("trigram fallback (catalog)", extra={"query": query_text[:60]})
        try:
            async with self._pool.connection() as conn:
                cur = await conn.execute(
                    "SELECT id_articulo, articulo, fecha_ultima_compra, "
                    "       similarity(articulo, %s) AS sim "
                    "FROM catalogo "
                    "WHERE is_active = TRUE AND similarity(articulo, %s) > %s "
                    "ORDER BY sim DESC LIMIT %s",
                    (query_text, query_text, TRGM_SIM_THRESHOLD, count))
                rows = await cur.fetchall()
            return [{"id_articulo": r[0], "articulo": r[1],
                     "fecha_ultima_compra": r[2].isoformat() if r[2] else None,
                     "similarity": float(r[3])} for r in rows]
        except Exception:
            logger.exception("trigram catalog fallback failed")
            return []

    async def _search_historical_trgm(self, query_text: str, count: int,
                                      threshold: float) -> list[dict]:
        logger.info("trigram fallback (historical)", extra={"query": query_text[:60]})
        try:
            async with self._pool.connection() as conn:
                cur = await conn.execute(
                    "SELECT h.id, h.user_text, h.catalog_description, "
                    "       similarity(h.user_text, %s) AS sim, h.id_articulo_catalogo "
                    "FROM historico_pedidos h "
                    "WHERE similarity(h.user_text, %s) > %s "
                    "ORDER BY sim DESC LIMIT %s",
                    (query_text, query_text, TRGM_SIM_THRESHOLD, count))
                rows = await cur.fetchall()
            return [{"id": r[0], "user_text": r[1], "catalog_description": r[2],
                     "similarity": float(r[3]), "id_articulo_catalogo": r[4]}
                    for r in rows]
        except Exception:
            logger.exception("trigram historical fallback failed")
            return []
