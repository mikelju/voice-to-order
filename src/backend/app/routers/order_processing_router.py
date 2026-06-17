# src/backend/app/routers/order_processing_router.py
"""The 5 order endpoints, ported from the original (auth removed — public local demo).

The /orders/send status-light semantics are ported literally: PDF impossible -> abort;
email failure -> warning; ERP failure -> global "fallido"; history failure -> warning.
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from ..models.order_models import (
    FinalizeOrderRequest,
    FinalizeOrderResponse,
    InitialOrderItem,
    ProcessAudioResponse,
    SearchArticlesRequest,
    SearchArticlesResponse,
    SearchedArticleItem,
    SendOrderRequest,
    SendOrderResponse,
)
from ..services.erp_simulator import erp_api_client
from ..services.historical_data_service import update_historical_data_service
from ..services.order_delivery_service import send_final_order_service
from ..services.order_finalization_service import create_final_order_structure_sync
from ..services.order_processing_service import process_order_text_service
from ..services.search_service import search_articles_service
from ..services.transcription_service import transcribe_audio_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/orders")

ERP_EXCLUDED_IDS = ["HERRAMIENTA", "OBSERVACION"]   # ported sentinels

# SEC-001 (audit 2026-06-17): bound the audio upload. 25 MB is Whisper's own limit;
# rejecting early avoids buffering huge bodies and burning real-mode quota.
MAX_AUDIO_BYTES = 25 * 1024 * 1024
ALLOWED_AUDIO_TYPES = {
    "audio/wav", "audio/x-wav", "audio/wave", "audio/vnd.wave",
    "audio/mpeg", "audio/mp3", "audio/mp4", "audio/m4a", "audio/x-m4a",
    "audio/webm", "audio/ogg", "application/octet-stream",
}


@router.post("/process-audio", response_model=ProcessAudioResponse)
async def process_audio_order(request: Request,
                              audio_file: UploadFile = File(...),
                              recording_id: Optional[int] = Form(default=None)):
    clients = request.app.state.clients

    # Warmup: heat the HNSW indexes while transcription runs (ported fire-and-forget;
    # the task reference is kept on app.state to avoid GC).
    searcher = clients.get("searcher")
    if searcher:
        request.app.state.warmup_task = asyncio.create_task(searcher.warmup())

    # review H5: an out-of-range recording_id is a client error, not a 500
    store = clients.get("replay")
    if recording_id is not None and store is not None and store.get(recording_id) is None:
        raise HTTPException(status_code=400,
                            detail=f"recording_id {recording_id} fuera de rango "
                                   f"(0..{len(store) - 1}).")

    # SEC-001: reject unsupported types and oversized uploads before any work.
    if audio_file.content_type and audio_file.content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=415, detail="Tipo de audio no soportado.")
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_AUDIO_BYTES + 4096:
        raise HTTPException(status_code=413,
                            detail="Audio demasiado grande (máximo 25 MB).")

    try:
        content = await audio_file.read(MAX_AUDIO_BYTES + 1)
        if len(content) > MAX_AUDIO_BYTES:
            raise HTTPException(status_code=413,
                                detail="Audio demasiado grande (máximo 25 MB).")
        transcribed = await transcribe_audio_service(
            clients, content, audio_file.filename or "", recording_id=recording_id)
        if transcribed is None:
            # SEC-002: do not echo the user-supplied filename back to the client.
            raise HTTPException(status_code=500,
                                detail="Fallo en la transcripción del audio.")
        transcription, _rid = transcribed

        processing = await process_order_text_service(clients, transcription)
        if processing is None:
            raise HTTPException(status_code=500,
                                detail="Fallo en el procesamiento del pedido (LLM).")

        warnings: list[str] = []
        num_order_raw = processing.get("num_order") or ""
        num_order = re.sub(r"\D", "", num_order_raw)   # ported normalization

        planta_name = processing.get("planta_name") or "Desconocido"
        planta_name_source = "llm"
        if num_order:
            status, erp_data = await erp_api_client.get_client_data_by_order_id(num_order)
            if status == "success" and erp_data:
                erp_planta_name = erp_data.get("Planta")
                if erp_planta_name:
                    planta_name = erp_planta_name
                    planta_name_source = "erp"
            elif status == "not_found":
                warnings.append(f"El Nº de Pedido '{num_order}' no se encontró en el ERP.")
            elif status == "error":
                warnings.append("No se pudo verificar el Nº de Pedido con el ERP. "
                                "Por favor, compruebe que el nombre de la planta es "
                                "correcto.")

        return ProcessAudioResponse(
            transcription=transcription,
            num_order=num_order or None,
            planta_name=planta_name,
            planta_name_source=planta_name_source,
            observaciones=processing.get("observaciones") or None,
            warnings=warnings,
            articles_list_original_text=processing.get("articles_list", []),
            df_order_json=[InitialOrderItem(**row)
                           for row in processing.get("df_order_list_of_dicts", [])],
            message="Audio procesado correctamente.",
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("process-audio failed")
        raise HTTPException(status_code=500, detail="Error interno procesando el audio.")


@router.get("/get-planta/{order_id}")
async def get_planta(order_id: str):
    if not order_id or not order_id.isdigit():
        raise HTTPException(status_code=400, detail="El ID del pedido debe ser numérico.")
    try:
        status, erp_data = await erp_api_client.get_client_data_by_order_id(order_id)
        if status == "success" and erp_data:
            return JSONResponse(status_code=200, content={
                "status": "success", "planta_name": erp_data.get("Planta")})
        if status == "not_found":
            return JSONResponse(status_code=404, content={
                "status": "not_found", "planta_name": None,
                "message": "El Nº de Parte no fue encontrado en el ERP."})
        return JSONResponse(status_code=503, content={
            "status": "error", "planta_name": None,
            "message": "No se pudo contactar con el ERP."})
    except Exception:
        logger.exception("get-planta failed")
        raise HTTPException(status_code=500, detail="Error interno consultando el ERP.")


@router.post("/search-articles", response_model=SearchArticlesResponse)
async def search_articles(request: Request, request_data: SearchArticlesRequest):
    if len(request_data.articles_list_original_text) != \
            len(request_data.description_list_for_search):
        raise HTTPException(status_code=400,
                            detail="Las listas de artículos y descripciones deben tener "
                                   "la misma longitud.")
    try:
        rows = await search_articles_service(
            request.app.state.clients,
            request_data.articles_list_original_text,
            request_data.description_list_for_search,
            num_opciones_busqueda=request_data.num_opciones_busqueda,
            historical_threshold=request_data.historical_threshold,
            catalog_threshold=request_data.catalog_threshold)
        return SearchArticlesResponse(
            searched_articles=[SearchedArticleItem(**row) for row in rows],
            message=f"Búsqueda completada: {len(rows)} candidatos.")
    except ValueError as exc:
        logger.exception("search-articles unavailable")
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception:
        logger.exception("search-articles failed")
        raise HTTPException(status_code=500, detail="Error interno en la búsqueda.")


@router.post("/finalize", response_model=FinalizeOrderResponse)
async def finalize_order(request_data: FinalizeOrderRequest):
    try:
        final_items, issues, warnings = create_final_order_structure_sync(
            request_data.selected_items)
        if final_items is None:
            raise HTTPException(status_code=500,
                                detail="No se pudo construir el pedido final.")
        return FinalizeOrderResponse(
            final_order_items=final_items,
            has_duplicates_or_issues=issues,
            warnings=warnings,
            message="Pedido finalizado.")
    except HTTPException:
        raise
    except Exception:
        logger.exception("finalize failed")
        raise HTTPException(status_code=500, detail="Error interno finalizando el pedido.")


@router.post("/send", response_model=SendOrderResponse)
async def send_order(request: Request, request_data: SendOrderRequest):
    clients = request.app.state.clients
    error_details_list: list[str] = []
    erp_critical_failure = False

    try:
        final_order_items_dict = [item.model_dump(by_alias=False)
                                  for item in request_data.final_order_items]
        plazo_str = request_data.plazo.isoformat() if request_data.plazo else ""

        # ---- Step 1: PDF + email (non-blocking except PDF) — ported semantics
        pdf_data, email_sent, email_error = await send_final_order_service(
            final_order_items_dict,
            request_data.num_order or "",
            request_data.planta_name or "",
            plazo_str,
            request_data.observaciones or "",
            request_data.enviar_a_obra,
            request_data.solo_imputar,
            user_email="demo@voice-to-order.local")

        if pdf_data is None:   # ported early-return: no PDF -> abort everything
            return SendOrderResponse(
                order_sent_status="fallido",
                historical_update_status="no_intentado",
                historical_update_message="Proceso abortado.",
                erp_update_status="no_intentado",
                erp_update_message="No se generó el PDF, proceso abortado.",
                pdf_download_data=None,
                message="Error crítico: no se pudo generar el PDF del pedido.",
                error_details=f"PDF: No generado ({email_error})")

        if email_error:
            error_details_list.append(f"Email: {email_error}")

        # ---- Step 2: ERP (blocking/critical) — ported
        erp_status: Optional[str] = "no_intentado"
        erp_message: Optional[str] = None
        if request_data.num_order:
            items_for_erp = [item for item in final_order_items_dict
                             if item.get("Ids") not in ERP_EXCLUDED_IDS]
            if not items_for_erp:
                erp_status = "omitido"
                erp_message = "Sin artículos para el ERP."
            else:
                erp_success, erp_message = await erp_api_client.send_order_to_erp(
                    order_id=request_data.num_order, items=items_for_erp)
                if erp_success:
                    erp_status = "exito"
                else:
                    erp_status = "fallido"
                    erp_critical_failure = True
                    error_details_list.append(f"ERP: {erp_message}")
        else:
            erp_status = "omitido"
            erp_message = "Sin número de pedido: envío al ERP omitido."

        # ---- Step 3: learned memory (non-blocking) — ported
        hist_status: Optional[str] = None
        hist_message: Optional[str] = None
        try:
            hist_result = await update_historical_data_service(
                clients,
                [item.model_dump() for item in request_data.items_for_history],
                request_data.num_order or "S_N_HIST")
            hist_status = hist_result.get("status")
            hist_message = hist_result.get("message")
            if hist_status in ("error", "partial_error"):
                error_details_list.append(f"Histórico: {hist_message}")
        except Exception as exc:
            logger.exception("historical update failed")
            hist_status = "error"
            hist_message = str(exc)
            error_details_list.append(f"Histórico: {exc}")

        # ---- Step 4: compose global status — ported literals
        final_error_details = " | ".join(error_details_list) if error_details_list \
            else None
        if erp_critical_failure:
            global_status = "fallido"
            final_message = "Error crítico: El pedido no se pudo registrar en el ERP."
        else:
            global_status = "enviado"
            final_message = ("Pedido procesado con advertencias."
                             if error_details_list else "Proceso completado.")

        return SendOrderResponse(
            order_sent_status=global_status,
            historical_update_status=hist_status,
            historical_update_message=hist_message,
            erp_update_status=erp_status,
            erp_update_message=erp_message,
            pdf_download_data=pdf_data,
            message=final_message,
            error_details=final_error_details)
    except Exception:
        logger.exception("send failed")
        raise HTTPException(status_code=500, detail="Error interno enviando el pedido.")
