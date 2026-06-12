# src/backend/app/routers/catalog_router.py
"""Manual catalog search (review-step "add manually"), ported from the original.

Ported as-is: AND of ILIKE %term% per word, limit 50, no is_active filter (the original
did not filter it here either — recorded gotcha).
"""
from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, HTTPException, Query, Request

from ..models.order_models import CatalogItem

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/catalog")


@router.get("/search", response_model=List[CatalogItem])
async def search_catalog(request: Request,
                         query: str = Query(..., min_length=3)):
    pool = request.app.state.clients.get("pool")
    if pool is None:
        raise HTTPException(status_code=500, detail="Base de datos no disponible.")
    terms = [t.strip() for t in query.lower().split() if t.strip()]
    if not terms:
        return []
    where = " AND ".join("articulo ILIKE %s" for _ in terms)
    params = [f"%{t}%" for t in terms]
    try:
        async with pool.connection() as conn:
            cur = await conn.execute(
                f"SELECT id_articulo, articulo FROM catalogo WHERE {where} LIMIT 50",
                params)
            rows = await cur.fetchall()
        return [CatalogItem(id_articulo=r[0], articulo=r[1]) for r in rows]
    except Exception:
        logger.exception("catalog search failed")
        raise HTTPException(status_code=500,
                            detail="Error interno buscando en el catálogo.")
