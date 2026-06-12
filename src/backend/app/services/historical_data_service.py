# src/backend/app/services/historical_data_service.py
"""Step 7, channel 3 — the learning loop: upsert confirmed lines into the memory.

Ported from the original's update_historical_data_service + upsert_historico_with_status
RPC, adapted to the replica schema (last_used_month instead of full timestamps).

Deviation (spec US-3): the upsert runs in BOTH modes — the learning loop is a core part
of what this repo demonstrates (the original gated it to ENVIRONMENT=production).
In real mode, new memory rows get a live embedding; in demo mode they stay without one
and remain reachable via the trigram fallback (declared limitation).
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from ..core.config import settings
from ..utils.text_utils import normalize_text

logger = logging.getLogger(__name__)

SKIP_DESCRIPTION = "--- SIN OPCIONES ---"   # ported sentinel


async def update_historical_data_service(clients: dict[str, Any],
                                         items_for_history: list[dict],
                                         order_number: str) -> dict:
    if "history" in settings.SIMULATE_FAILURE:
        raise ConnectionError("Fallo simulado del histórico (SIMULATE_FAILURE)")

    pool = clients.get("pool")
    if pool is None:
        return {"status": "error", "message": "Sin conexión a la base de datos.",
                "errors": len(items_for_history)}

    month = datetime.now().strftime("%Y-%m")
    new_rows: list[tuple[int, str]] = []   # (historico_id, normalized_text)
    errors = 0
    processed = 0

    for item in items_for_history:
        description = item.get("Descripción", "")
        if not description or description == SKIP_DESCRIPTION:
            continue
        user_text = normalize_text(item.get("Artículo", ""))
        if not user_text:
            continue
        try:
            async with pool.connection() as conn:
                cur = await conn.execute(
                    "SELECT historico_id, is_new FROM upsert_historico_with_status"
                    "(%s, %s, %s, %s)",
                    (user_text, description, item.get("Ids"), month))
                row = await cur.fetchone()
            processed += 1
            if row and row[1]:
                new_rows.append((row[0], user_text))
        except Exception:
            logger.exception("Historical upsert failed for '%s'", user_text[:50])
            errors += 1

    embedded = await _embed_new_rows(clients, new_rows)

    if errors and processed:
        status = "partial_error"
    elif errors:
        status = "error"
    else:
        status = "success"
    message = (f"Histórico actualizado: {processed} líneas ({len(new_rows)} nuevas, "
               f"{embedded} con embedding), {errors} errores.")
    return {"status": status, "message": message, "errors": errors}


async def _embed_new_rows(clients: dict[str, Any],
                          new_rows: list[tuple[int, str]]) -> int:
    """Real mode: embed new memory rows so they are vector-searchable immediately."""
    if not new_rows or settings.APP_MODE == "demo":
        return 0
    embedder = clients.get("embedder")
    pool = clients.get("pool")
    if embedder is None or pool is None:
        return 0
    texts = [text for _, text in new_rows]
    vectors = await embedder.embed_documents(texts)
    if not vectors:
        return 0
    inserted = 0
    try:
        async with pool.connection() as conn:
            for (historico_id, _), vec in zip(new_rows, vectors):
                await conn.execute(
                    "INSERT INTO historico_embeddings (historico_id, embedding) "
                    "VALUES (%s, %s::vector) ON CONFLICT (historico_id) DO UPDATE "
                    "SET embedding = EXCLUDED.embedding",
                    (historico_id, "[" + ",".join(repr(float(x)) for x in vec) + "]"))
                inserted += 1
    except Exception:
        logger.exception("Embedding insert for new memory rows failed")
    return inserted
