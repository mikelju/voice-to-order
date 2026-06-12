# tests/backend/test_order_models.py
"""Contract tests: the ported Pydantic models keep the original field names (accents
included) and validations. Spec: data contracts ported 1:1."""
import pytest
from pydantic import ValidationError

from src.backend.app.models.order_models import (
    FinalOrderLineItem,
    InitialOrderItem,
    SearchArticlesRequest,
    SearchedArticleItem,
    SendOrderResponse,
    UserSelectedItem,
)


def test_initial_order_item_accented_fields():
    item = InitialOrderItem(**{"CANTIDAD": 2.5, "ARTÍCULO": "tubo inox",
                               "DESCRIPCIÓN": "ML TUBO DN20 INOX"})
    dumped = item.model_dump()
    assert dumped["ARTÍCULO"] == "tubo inox"
    assert dumped["DESCRIPCIÓN"] == "ML TUBO DN20 INOX"
    assert dumped["CANTIDAD"] == 2.5


def test_final_line_keeps_accented_descripcion():
    line = FinalOrderLineItem(Uds=1.0, Ids="ART-0123456789",
                              **{"Descripción": "VALVULA BOLA 1/2"})
    assert "Descripción" in line.model_dump()


def test_user_selected_item_rejects_non_positive_quantity():
    with pytest.raises(ValidationError):
        UserSelectedItem(original_article_text="x", selected_catalog_description="d",
                         selected_catalog_id="ART-1", quantity=0)


def test_search_request_defaults_are_the_original_constants():
    req = SearchArticlesRequest(articles_list_original_text=["a"],
                                description_list_for_search=["d"])
    assert req.num_opciones_busqueda == 25
    assert req.historical_threshold == 0.75
    assert req.catalog_threshold == 0.5


def test_search_request_bounds():
    with pytest.raises(ValidationError):
        SearchArticlesRequest(articles_list_original_text=[],
                              description_list_for_search=[],
                              num_opciones_busqueda=101)


def test_searched_item_carries_memory_flags():
    item = SearchedArticleItem(Article="taco de 10", Ids="ART-1", Description="TACO 10",
                               Score=0.91, Date_score=1, Historical_match=True)
    assert item.Historical_match is True
    assert item.Fecha_ultima_compra is None


def test_send_order_response_status_literals():
    resp = SendOrderResponse(order_sent_status="enviado", erp_update_status="omitido")
    assert resp.order_sent_status == "enviado"
    assert resp.pdf_download_data is None
