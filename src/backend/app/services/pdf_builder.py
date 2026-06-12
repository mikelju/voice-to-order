# src/backend/app/services/pdf_builder.py
"""Order PDF (reportlab), ported from the original's order_management.py.

Differences from the original (recorded in the phase plan):
- no client logos (public replica; Phase 5 may add the Biar Tech brand);
- no "Últ. Proveedor" column — the supplier column was dropped from the public dataset.
Everything else mirrors the original layout: title, Fecha/Usuario/Num Parte/Planta/Plazo,
[X]/[ ] checkboxes for "Enviar a Obra" / "Sólo imputar al parte", escaped observaciones,
article table with 7pt cells and repeated header row.
"""
from __future__ import annotations

import html
import tempfile
from datetime import datetime
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..core.config import settings


def generate_order_pdf(final_order_items: list[dict], planta_name: str, num_order: str,
                       user_email: str, plazo_str: str, observaciones: str,
                       enviar_a_obra: bool, solo_imputar: bool) -> str:
    """Build the PDF and return its temp-file path (caller deletes it)."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.close()

    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle("cell", parent=styles["Normal"], fontSize=7, leading=9)
    story = []

    story.append(Paragraph("Pedido de Material", styles["Title"]))
    story.append(Spacer(1, 12))

    tz = ZoneInfo(settings.TIMEZONE)
    fields = [
        ("Fecha", datetime.now(tz).strftime("%d/%m/%Y %H:%M")),
        ("Usuario", user_email or "-"),
        ("Num Parte", num_order or "S/N"),
        ("Planta", planta_name or "S/P"),
        ("Plazo", plazo_str or "-"),
        ("Enviar a Obra", "[X]" if enviar_a_obra else "[ ]"),
        ("Sólo imputar al parte", "[X]" if solo_imputar else "[ ]"),
    ]
    for label, value in fields:
        story.append(Paragraph(f"<b>{label}:</b> {html.escape(str(value))}",
                               styles["Normal"]))
    if observaciones:
        safe = html.escape(observaciones).replace("\n", "<br/>")
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"<b>Observaciones:</b> {safe}", styles["Normal"]))
    story.append(Spacer(1, 12))

    header = ["Uds", "Código", "Descripción"]
    table_data = [[Paragraph(f"<b>{h}</b>", cell_style) for h in header]]
    for item in final_order_items:
        table_data.append([
            Paragraph(html.escape(str(item.get("Uds", ""))), cell_style),
            Paragraph(html.escape(str(item.get("Ids", ""))), cell_style),
            Paragraph(html.escape(str(item.get("Descripción", ""))), cell_style),
        ])
    table = Table(table_data, colWidths=[0.6 * inch, 1.4 * inch, 4.7 * inch],
                  repeatRows=1)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(table)

    doc = SimpleDocTemplate(tmp.name, pagesize=A4, title="Pedido de Material")
    doc.build(story)
    return tmp.name
