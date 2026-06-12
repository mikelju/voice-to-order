# src/backend/app/models/order_models.py
"""Pydantic request/response contracts, ported 1:1 from the original.

The accented field names (Descripción, Artículo, ARTÍCULO, DESCRIPCIÓN, CANTIDAD) are
deliberate: they travel verbatim in the API JSON and the frontend depends on them. Do not
"normalize" them.

Replica fix (documented in the phase plan): `Fecha_ultima_compra` is actually populated —
the original built the row with a 'Fecha ultima compra' key (spaces) that never matched
the model field, so the API always returned null there.
"""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class InitialOrderItem(BaseModel):
    CANTIDAD: float
    ARTÍCULO: str
    DESCRIPCIÓN: str


class ProcessAudioResponse(BaseModel):
    transcription: str
    num_order: Optional[str] = None
    planta_name: Optional[str] = None
    planta_name_source: str = "llm"          # "llm" | "erp"
    observaciones: Optional[str] = None
    warnings: List[str] = []
    articles_list_original_text: List[str] = []
    df_order_json: List[InitialOrderItem] = []
    message: str = ""


class SearchArticlesRequest(BaseModel):
    articles_list_original_text: List[str]
    description_list_for_search: List[str]
    num_opciones_busqueda: int = Field(default=25, gt=0, le=100)
    historical_threshold: float = Field(default=0.75, ge=0, le=1)
    catalog_threshold: float = Field(default=0.5, ge=0, le=1)


class SearchedArticleItem(BaseModel):
    Article: str
    Ids: str
    Description: str
    Score: float
    Date_score: float                         # 1 = memory hit, 0 = catalog
    Fecha_ultima_compra: Optional[str] = None
    Historical_match: bool


class SearchArticlesResponse(BaseModel):
    searched_articles: List[SearchedArticleItem]
    message: str = ""


class UserSelectedItem(BaseModel):
    original_article_text: str
    selected_catalog_description: str
    selected_catalog_id: str
    quantity: float = Field(gt=0)


class FinalizeOrderRequest(BaseModel):
    selected_items: List[UserSelectedItem]
    num_order: Optional[str] = None
    planta_name: Optional[str] = None
    plazo: Optional[date] = None


class FinalOrderLineItem(BaseModel):
    Uds: float
    Ids: str
    Descripción: str


class FinalizeOrderResponse(BaseModel):
    final_order_items: List[FinalOrderLineItem]
    has_duplicates_or_issues: bool = False
    warnings: List[str] = []
    message: str = ""


class ItemForHistory(BaseModel):
    Ids: str
    Artículo: str
    Descripción: str


class SendOrderRequest(BaseModel):
    final_order_items: List[FinalOrderLineItem]
    items_for_history: List[ItemForHistory] = []
    num_order: Optional[str] = None
    planta_name: Optional[str] = None
    plazo: Optional[date] = None
    observaciones: Optional[str] = None
    enviar_a_obra: bool = False
    solo_imputar: bool = False


class PDFDownloadData(BaseModel):
    b64_pdf: str
    filename: str
    content_type: str = "application/pdf"


class SendOrderResponse(BaseModel):
    order_sent_status: str                    # "enviado" | "fallido"
    historical_update_status: Optional[str] = None   # skipped|success|partial_error|error|no_intentado
    historical_update_message: Optional[str] = None
    erp_update_status: Optional[str] = None   # no_intentado|omitido|exito|fallido
    erp_update_message: Optional[str] = None
    pdf_download_data: Optional[PDFDownloadData] = None
    message: str = ""
    error_details: Optional[str] = None


class CatalogItem(BaseModel):
    id_articulo: str
    articulo: str


class DemoRecording(BaseModel):
    recording_id: int
    transcription: str
    n_items: int
