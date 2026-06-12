# src/backend/app/services/search_service.py
"""Steps 4-5 — Per-article parallel search + re-rank.

Ported design (the signature decision of the original):
- one asyncio task per article, asyncio.gather(return_exceptions=True): a failing article
  is logged and dropped, the rest of the order survives;
- two named semaphores bound the fan-out: LLM=10, DB=10;
- memory-first (buscar_historicos, threshold 0.75, count 1) with the hit re-validated
  against the live catalog (is_active + live description), then catalog
  (buscar_articulos, threshold 0.5, top 25) deduped against the memory hit;
- re-rank per article under the LLM semaphore; on ANY failure the deterministic fallback
  sorts by (Historical_match desc, Score desc). Ranking can degrade; it cannot error.

demo mode: the deterministic fallback IS the ranking (no recorded re-rank replays; the
fallback is original production behavior — decision recorded in the phase plan).

The original used pandas for the final sort; replicated here with plain sorted().
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

from ..core.config import settings
from ..core.llm_wrapper import get_llm_completion
from ..core.prompts import RANKING_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

LLM_CONCURRENCY_LIMIT = 10   # ported
DB_CONCURRENCY_LIMIT = 10    # ported


def _call_llm_for_reranking_sync(articles_dict_json_str: str) -> Optional[str]:
    messages = [
        {"role": "system", "content": RANKING_SYSTEM_PROMPT},
        {"role": "user", "content": (
            "Ordena los siguientes resultados según las instrucciones. Aquí tienes el "
            "JSON (los values son diccionarios con 'article', 'description', 'source', "
            f"'similarity_score'):\n{articles_dict_json_str}")},
    ]
    return get_llm_completion(model_name=settings.RANKING_LLM_MODEL, messages=messages,
                              temperature=0.1, response_format={"type": "json_object"})


def deterministic_rank(rows: list[dict]) -> list[dict]:
    """Ported fallback: sort by (Historical_match desc, Score desc)."""
    return sorted(rows, key=lambda r: (not r["Historical_match"], -r["Score"]))


async def _rerank(rows: list[dict], llm_semaphore: asyncio.Semaphore) -> list[dict]:
    if not rows:
        return rows
    if settings.APP_MODE == "demo":
        return deterministic_rank(rows)

    async with llm_semaphore:
        payload = {
            row["temp_id"]: {
                "article": row["Article"], "description": row["Description"],
                "source": "historical" if row["Historical_match"] else "catalog",
                "similarity_score": row["Score"],
            } for row in rows
        }
        response = await asyncio.to_thread(
            _call_llm_for_reranking_sync,
            json.dumps(payload, ensure_ascii=False, indent=2))
    try:
        ordered_ids = json.loads(response)["ordered_ids"]
        order_map = {tid: pos for pos, tid in enumerate(ordered_ids)}
        return sorted(rows, key=lambda r: order_map.get(r["temp_id"], float("inf")))
    except Exception:
        logger.warning("Re-rank LLM failed; deterministic fallback applied")
        return deterministic_rank(rows)


async def _search_single_article_async(idx: int, article_text_orig: str,
                                       desc_for_catalog_search: str, searcher: Any,
                                       historical_threshold: float,
                                       catalog_threshold: float,
                                       num_opciones_busqueda: int,
                                       llm_semaphore: asyncio.Semaphore,
                                       db_semaphore: asyncio.Semaphore) -> list[dict]:
    rows: list[dict] = []
    best_historical_desc: Optional[str] = None

    async with db_semaphore:
        # memory first: the dictated text is the query (ported)
        historical = await searcher.search_historical(
            query_text=article_text_orig, threshold=historical_threshold, count=1)
        if historical:
            best = historical[0]
            id_from_history = best.get("id_articulo_catalogo")
            if id_from_history:
                details = await searcher.get_catalog_item_details(id_from_history)
                if details:   # live description, only while is_active (ported)
                    best_historical_desc = details["articulo"]
                    rows.append({
                        "temp_id": f"{idx}_h", "Article": article_text_orig,
                        "Ids": details["id_articulo"],
                        "Description": best_historical_desc,
                        "Score": float(best["similarity"]), "Date_score": 1,
                        "Fecha_ultima_compra": details["fecha_ultima_compra"],
                        "Historical_match": True,
                    })
        # catalog search uses the LLM-processed description (ported)
        catalog = await searcher.search_catalog(
            query_text=desc_for_catalog_search, threshold=catalog_threshold,
            count=num_opciones_busqueda)
        for i, result in enumerate(catalog):
            candidate_desc = result.get("articulo")
            if best_historical_desc and candidate_desc == best_historical_desc:
                continue   # dedupe against the memory hit (ported)
            rows.append({
                "temp_id": f"{idx}_c{i}", "Article": article_text_orig,
                "Ids": result.get("id_articulo", "-"),
                "Description": candidate_desc or "N/A",
                "Score": float(result["similarity"]), "Date_score": 0,
                "Fecha_ultima_compra": result.get("fecha_ultima_compra"),
                "Historical_match": False,
            })

    return await _rerank(rows, llm_semaphore)


async def search_articles_service(clients: dict[str, Any],
                                  articles_list_original_text: list[str],
                                  description_list_for_search: list[str],
                                  num_opciones_busqueda: int = 25,
                                  historical_threshold: float = 0.75,
                                  catalog_threshold: float = 0.5) -> list[dict]:
    searcher = clients.get("searcher")
    if searcher is None:
        raise ValueError("Searcher not initialized (app.state.clients)")

    llm_semaphore = asyncio.Semaphore(LLM_CONCURRENCY_LIMIT)
    db_semaphore = asyncio.Semaphore(DB_CONCURRENCY_LIMIT)

    tasks = [
        _search_single_article_async(idx, article_text, desc_search, searcher,
                                     historical_threshold, catalog_threshold,
                                     num_opciones_busqueda, llm_semaphore, db_semaphore)
        for idx, (article_text, desc_search)
        in enumerate(zip(articles_list_original_text, description_list_for_search))
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_rows: list[dict] = []
    for i, result in enumerate(results):
        if isinstance(result, BaseException):
            logger.error("Search task for article '%s' failed: %r",
                         articles_list_original_text[i], result)
            continue
        for row in result:
            row["Article_Order"] = i
            all_rows.append(row)

    all_rows.sort(key=lambda r: r.get("Article_Order", float("inf")))
    for row in all_rows:
        row.pop("Article_Order", None)
        row.pop("temp_id", None)
    return all_rows
