# src/backend/app/services/order_delivery_service.py
"""Step 7, channel 1+2 — PDF (real) + email (simulated), non-blocking semantics ported.

Differences from the original (recorded in the phase plan):
- no ultimo_proveedor enrichment (the supplier column was dropped from the public dataset);
- the latent tuple-order bug of the original's early return is fixed: this function
  ALWAYS returns (pdf_download_data | None, email_sent: bool, error_msg | None).
"""
from __future__ import annotations

import asyncio
import base64
import logging
import os
import re
from typing import Optional

from ..core.config import settings
from .email_simulator import email_sender_instance
from .pdf_builder import generate_order_pdf

logger = logging.getLogger(__name__)


def _safe(fragment: str, default: str) -> str:
    out = re.sub(r"[^A-Za-z0-9]+", "_", fragment or "").strip("_")
    return out or default


async def send_final_order_service(final_order_items: list[dict], num_order: str,
                                   planta_name: str, plazo_str: str, observaciones: str,
                                   enviar_a_obra: bool, solo_imputar: bool,
                                   user_email: str
                                   ) -> tuple[Optional[dict], bool, Optional[str]]:
    pdf_path: Optional[str] = None
    try:
        # 1) PDF (the abort-everything channel: no PDF -> no order)
        try:
            from datetime import datetime
            filename = (f"pedido_{_safe(num_order, 'S_N')}_"
                        f"{_safe(planta_name, 'S_P')}_"
                        f"{datetime.now().strftime('%Y%m%d_%H%M')}.pdf")
            pdf_path = await asyncio.to_thread(
                generate_order_pdf, final_order_items, planta_name, num_order,
                user_email, plazo_str, observaciones, enviar_a_obra, solo_imputar)
            with open(pdf_path, "rb") as f:
                b64_pdf = base64.b64encode(f.read()).decode("ascii")
            pdf_download_data = {"b64_pdf": b64_pdf, "filename": filename,
                                 "content_type": "application/pdf"}
        except Exception as exc:
            logger.exception("PDF generation failed")
            return None, False, f"No se pudo generar el PDF: {exc}"

        # 2) Email (simulated channel; failure never aborts — ported)
        email_sent = False
        email_error: Optional[str] = None
        try:
            order_data = {"num_order": num_order, "planta_name": planta_name,
                          "plazo": plazo_str, "observaciones": observaciones,
                          "solo_imputar": solo_imputar}
            email_sent = await email_sender_instance.send_email_async(
                pdf_path, order_data, sender_email="demo@voice-to-order.local")
            if not email_sent:
                email_error = "El email (simulado) no se pudo enviar."
        except Exception as exc:
            logger.exception("Email channel failed")
            email_error = f"Error en el canal de email: {exc}"

        return pdf_download_data, email_sent, email_error
    finally:
        if pdf_path:
            try:
                os.remove(pdf_path)
            except OSError:
                logger.warning("Could not remove temp PDF %s", pdf_path)
