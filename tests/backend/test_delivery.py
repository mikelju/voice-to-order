# tests/backend/test_delivery.py
"""Delivery channels: real PDF, simulated email (cutoff 14h + retry), simulated ERP
(payload shape + sentinels), and the SIMULATE_FAILURE chaos switch. Spec US-3."""
import base64
import json
from datetime import datetime

import pytest

from src.backend.app.services import email_simulator as email_mod
from src.backend.app.services import erp_simulator as erp_mod
from src.backend.app.services import order_delivery_service as delivery
from src.backend.app.services.email_simulator import EmailSimulator, select_recipients
from src.backend.app.services.erp_simulator import ErpSimulator

LINES = [{"Uds": 2.0, "Ids": "ART-0123456789", "Descripción": "TACO 10 PLASTICO"},
         {"Uds": 1.0, "Ids": "HERRAMIENTA", "Descripción": "taladro (no ERP)"}]


# --- ERP simulator -------------------------------------------------------------------

async def test_erp_plant_lookup_deterministic():
    erp = ErpSimulator()
    status, data = await erp.get_client_data_by_order_id("10001")
    assert status == "success" and data["Planta"]
    again = await erp.get_client_data_by_order_id("10001")
    assert again[1]["Planta"] == data["Planta"]


async def test_erp_ids_ending_in_9_not_found():
    erp = ErpSimulator()
    status, data = await erp.get_client_data_by_order_id("10009")
    assert status == "not_found" and data is None


async def test_erp_send_writes_original_payload_shape(tmp_path, monkeypatch):
    monkeypatch.setattr(erp_mod.settings, "ERP_DIR", str(tmp_path))
    monkeypatch.setattr(erp_mod.settings, "SIMULATE_FAILURE", "")
    erp = ErpSimulator()
    ok, msg = await erp.send_order_to_erp("10001", [LINES[0]])
    assert ok is True
    written = json.loads(next(tmp_path.glob("order_*.json")).read_text("utf-8"))
    assert written == {"IdParte": 10001,
                       "Lineas": [{"IdArticulo": "ART-0123456789", "Cantidad": 2.0}]}


async def test_erp_chaos_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(erp_mod.settings, "ERP_DIR", str(tmp_path))
    monkeypatch.setattr(erp_mod.settings, "SIMULATE_FAILURE", "erp,email")
    erp = ErpSimulator()
    ok, msg = await erp.send_order_to_erp("10001", [LINES[0]])
    assert ok is False and "simulado" in msg.lower()
    assert not list(tmp_path.glob("*.json"))


# --- email simulator ----------------------------------------------------------------

def test_recipients_workday_cutoff():
    weekday_morning = datetime(2026, 6, 10, 9, 0)     # Wednesday 9:00
    weekday_late = datetime(2026, 6, 10, 15, 0)       # Wednesday 15:00
    sunday = datetime(2026, 6, 14, 9, 0)
    assert select_recipients(weekday_morning) == email_mod.RECIPIENTS_WORKDAY
    assert select_recipients(weekday_late) == email_mod.RECIPIENTS_OFFHOURS
    assert select_recipients(sunday) == email_mod.RECIPIENTS_OFFHOURS


async def test_email_writes_outbox_message(tmp_path, monkeypatch):
    monkeypatch.setattr(email_mod.settings, "OUTBOX_DIR", str(tmp_path))
    monkeypatch.setattr(email_mod.settings, "SIMULATE_FAILURE", "")
    sim = EmailSimulator()
    ok = await sim.send_email_async("pedido_x.pdf",
                                    {"num_order": "10001", "planta_name": "Planta Norte",
                                     "plazo": "2026-06-15", "solo_imputar": False},
                                    "demo@voice-to-order.local")
    assert ok is True
    msg = json.loads(next(tmp_path.glob("email_*.json")).read_text("utf-8"))
    assert msg["subject"].startswith("Pedido Planta Norte 10001")
    assert msg["attachment"] == "pedido_x.pdf"


async def test_email_chaos_retries_x3_then_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(email_mod.settings, "OUTBOX_DIR", str(tmp_path))
    monkeypatch.setattr(email_mod.settings, "SIMULATE_FAILURE", "email")
    sleeps: list[float] = []

    async def fake_sleep(s):
        sleeps.append(s)

    monkeypatch.setattr(email_mod.asyncio, "sleep", fake_sleep)
    sim = EmailSimulator()
    ok = await sim.send_email_async("p.pdf", {"solo_imputar": True}, "demo@x.local")
    assert ok is False
    assert sleeps == [2, 4]   # ported backoff attempt*2
    assert not list(tmp_path.glob("*.json"))


# --- PDF + combined delivery ---------------------------------------------------------

async def test_send_final_order_returns_pdf_b64(monkeypatch, tmp_path):
    monkeypatch.setattr(email_mod.settings, "OUTBOX_DIR", str(tmp_path))
    monkeypatch.setattr(email_mod.settings, "SIMULATE_FAILURE", "")
    pdf_data, email_sent, error = await delivery.send_final_order_service(
        LINES, "10001", "Planta Norte", "2026-06-15", "obs", False, False,
        "demo@x.local")
    assert error is None and email_sent is True
    assert pdf_data["filename"].startswith("pedido_10001_Planta_Norte_")
    raw = base64.b64decode(pdf_data["b64_pdf"])
    assert raw[:5] == b"%PDF-"


async def test_send_final_order_email_failure_does_not_abort(monkeypatch, tmp_path):
    monkeypatch.setattr(email_mod.settings, "OUTBOX_DIR", str(tmp_path))
    monkeypatch.setattr(email_mod.settings, "SIMULATE_FAILURE", "email")

    async def fake_sleep(s):
        return None

    monkeypatch.setattr(email_mod.asyncio, "sleep", fake_sleep)
    pdf_data, email_sent, error = await delivery.send_final_order_service(
        LINES, "10001", "Planta Norte", "", "", False, False, "demo@x.local")
    assert pdf_data is not None          # PDF survives
    assert email_sent is False and error is not None
