# src/backend/app/services/order_processing_service.py
"""Step 3 — Extract the structured order.

real mode: LLM (model from PROCESSING_LLM_MODEL, JSON mode, temperature 0.1) guarded by
RETRY x3 with 2s·attempt backoff — ported from the original after its truncated-JSON
incident (fix-4 there). The robust _parse_llm_response is ported too.

demo mode: replay of the recorded pair. The pair stores the confirmed catalog lines
(post-matching ground truth), so ARTÍCULO and DESCRIPCIÓN both carry the confirmed
description (decision recorded in the phase plan; demo scores are optimistic and the
public README declares it).
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any, Optional

from ..core.config import settings
from ..core.llm_wrapper import get_llm_completion
from ..core.prompts import TRANSCRIPTION_SYSTEM_PROMPT, TRANSCRIPTION_USER_PROMPT

logger = logging.getLogger(__name__)

MAX_LLM_RETRIES = 3          # 1 original attempt + 2 retries (ported)
RETRY_DELAY_SECONDS = 2      # real delay = RETRY_DELAY_SECONDS * attempt -> 2s, 4s

DEMO_NUM_ORDER_BASE = 10001  # demo num_order = base + recording_id (resolvable by the
                             # simulated ERP, so the full plant-lookup path is exercised)


def _parse_llm_response(response_text: str) -> Optional[str]:
    """Ported: accept valid JSON, else extract {...} and retry with quote fixing."""
    try:
        json.loads(response_text)
        return response_text
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", response_text, re.DOTALL)
    if match:
        corrected = match.group(0).replace("'", '"')
        try:
            json.loads(corrected)
            return corrected
        except json.JSONDecodeError:
            return None
    return None


def _call_llm_for_order_processing_sync(transcription: str) -> Optional[str]:
    messages = [
        {"role": "system", "content": TRANSCRIPTION_SYSTEM_PROMPT},
        {"role": "user",
         "content": TRANSCRIPTION_USER_PROMPT.replace(r"{{TRANSCRIPT}}", transcription)},
    ]
    for attempt in range(1, MAX_LLM_RETRIES + 1):
        logger.info("Calling extraction LLM", extra={"attempt": attempt})
        try:
            response_text = get_llm_completion(
                model_name=settings.PROCESSING_LLM_MODEL, messages=messages,
                temperature=0.1, response_format={"type": "json_object"})
            if response_text is None:
                logger.error("get_llm_completion returned None", extra={"attempt": attempt})
            else:
                result = _parse_llm_response(response_text)
                if result is not None:
                    return result
        except Exception:
            logger.exception("Extraction LLM call failed", extra={"attempt": attempt})
        if attempt < MAX_LLM_RETRIES:
            delay = RETRY_DELAY_SECONDS * attempt
            logger.warning("Retrying extraction LLM in %ss (%s/%s)",
                           delay, attempt, MAX_LLM_RETRIES)
            time.sleep(delay)   # runs inside asyncio.to_thread (ported)
    logger.error("Extraction LLM failed after %s attempts", MAX_LLM_RETRIES)
    return None


def _result_from_json(payload: dict) -> Optional[dict]:
    quantities = payload.get("CANTIDAD", [])
    articles = payload.get("ARTÍCULO", [])
    descriptions = [str(d).replace('"', "") for d in payload.get("DESCRIPCIÓN", [])]
    if not (len(quantities) == len(articles) == len(descriptions)):
        logger.error("Extraction lists length mismatch: %s/%s/%s",
                     len(quantities), len(articles), len(descriptions))
        return None
    rows = [{"CANTIDAD": float(q), "ARTÍCULO": str(a), "DESCRIPCIÓN": d}
            for q, a, d in zip(quantities, articles, descriptions)]
    return {
        "articles_list": [str(a) for a in articles],
        "df_order_list_of_dicts": rows,
        "num_order": str(payload.get("NUM_ORDER", "S/N")),
        "client_name": str(payload.get("CLIENT", "No Encontrado")),
        "planta_name": "Desconocido",
        "observaciones": str(payload.get("OBSERVACIONES", "") or ""),
        "description_list_for_search": descriptions,
    }


async def process_order_text_service(clients: dict[str, Any], transcription_text: str
                                     ) -> Optional[dict]:
    if settings.APP_MODE == "demo":
        return _process_demo(clients, transcription_text)

    raw = await asyncio.to_thread(_call_llm_for_order_processing_sync, transcription_text)
    if raw is None:
        return None
    try:
        return _result_from_json(json.loads(raw))
    except (json.JSONDecodeError, ValueError, TypeError):
        logger.exception("Extraction JSON unusable")
        return None


def _process_demo(clients: dict[str, Any], transcription_text: str) -> Optional[dict]:
    store = clients.get("replay")
    if store is None:
        logger.error("Demo mode without replay store")
        return None
    rid = store.find_by_transcription(transcription_text)
    if rid is None:
        logger.error("Transcription not found in replay store")
        return None
    pair = store.get(rid)
    items = pair["expected_items"]
    rows = [{"CANTIDAD": float(i["qty"]), "ARTÍCULO": i["description"],
             "DESCRIPCIÓN": i["description"]} for i in items]
    logger.info("Demo replay extraction", extra={"recording_id": rid, "items": len(rows)})
    return {
        "articles_list": [i["description"] for i in items],
        "df_order_list_of_dicts": rows,
        "num_order": str(DEMO_NUM_ORDER_BASE + rid),
        "client_name": "[customer]",
        "planta_name": "Desconocido",
        "observaciones": "",
        "description_list_for_search": [i["description"] for i in items],
    }
