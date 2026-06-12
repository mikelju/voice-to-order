# src/backend/app/services/order_finalization_service.py
"""Step 6 support — build the final order structure from the user's selections (ported)."""
from __future__ import annotations

import logging
from typing import Optional

from ..models.order_models import UserSelectedItem

logger = logging.getLogger(__name__)


def create_final_order_structure_sync(user_selected_items: list[UserSelectedItem]
                                      ) -> tuple[Optional[list[dict]], bool, list[str]]:
    """Return (final_items, has_issues, warnings). Ported semantics: empty selection is
    a warning, non-positive quantities are skipped with a warning."""
    if not user_selected_items:
        return [], False, ["No se seleccionaron artículos para el pedido."]

    final_items: list[dict] = []
    warnings: list[str] = []
    issues_found = False
    for item in user_selected_items:
        try:
            uds = float(item.quantity)
        except (TypeError, ValueError):
            warnings.append(f"Cantidad no numérica para '{item.original_article_text}'; "
                            "línea omitida.")
            issues_found = True
            continue
        if uds <= 0:
            warnings.append(f"Cantidad no válida ({uds}) para "
                            f"'{item.original_article_text}'; línea omitida.")
            issues_found = True
            continue
        final_items.append({
            "Uds": uds,
            "Ids": item.selected_catalog_id,
            "Descripción": item.selected_catalog_description,
        })
    return final_items, issues_found, warnings
