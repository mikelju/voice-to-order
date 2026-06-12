# tests/backend/test_finalization.py
"""Finalize-step validation (ported semantics). Spec US-3."""
from src.backend.app.models.order_models import UserSelectedItem
from src.backend.app.services.order_finalization_service import (
    create_final_order_structure_sync,
)


def make_item(qty=2.0, text="taco de 10", desc="TACO 10", art="ART-1"):
    return UserSelectedItem(original_article_text=text,
                            selected_catalog_description=desc,
                            selected_catalog_id=art, quantity=qty)


def test_empty_selection_warns_without_issues():
    items, issues, warnings = create_final_order_structure_sync([])
    assert items == [] and issues is False
    assert warnings and "No se seleccionaron" in warnings[0]


def test_builds_final_lines_with_accented_key():
    items, issues, warnings = create_final_order_structure_sync(
        [make_item(qty=2.5), make_item(qty=1, desc="TUERCA M10", art="ART-2")])
    assert issues is False and warnings == []
    assert items[0] == {"Uds": 2.5, "Ids": "ART-1", "Descripción": "TACO 10"}
    assert items[1]["Ids"] == "ART-2"


def test_decimal_quantities_supported():
    items, _, _ = create_final_order_structure_sync([make_item(qty=6.5)])
    assert items[0]["Uds"] == 6.5
