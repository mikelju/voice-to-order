# tests/backend/test_extraction.py
"""Step-3 extraction: demo replay contract + real-mode retry x3 with 2s·attempt backoff
and the robust JSON parser (ported). Spec US-1."""
import json

import pytest

from src.backend.app.services import order_processing_service as ops
from src.backend.app.services.replay_store import ReplayStore

PAIR = {"transcription": "Pedido [customer] [order-ref], 2 tacos de 10",
        "expected_items": [{"qty": "2.0", "description": "TACO 10 PLASTICO"},
                           {"qty": "1.0", "description": "TUERCA M10 INOX DIN 934"}]}


def make_store():
    return ReplayStore([PAIR])


# --- demo replay -----------------------------------------------------------------

async def test_demo_replay_extraction_contract(monkeypatch):
    monkeypatch.setattr(ops.settings, "APP_MODE", "demo")
    clients = {"replay": make_store()}
    out = await ops.process_order_text_service(clients, PAIR["transcription"])
    assert out is not None
    rows = out["df_order_list_of_dicts"]
    assert rows[0] == {"CANTIDAD": 2.0, "ARTÍCULO": "TACO 10 PLASTICO",
                       "DESCRIPCIÓN": "TACO 10 PLASTICO"}
    assert out["num_order"] == str(ops.DEMO_NUM_ORDER_BASE)   # recording 0
    assert out["description_list_for_search"] == ["TACO 10 PLASTICO",
                                                  "TUERCA M10 INOX DIN 934"]


async def test_demo_unknown_transcription_returns_none(monkeypatch):
    monkeypatch.setattr(ops.settings, "APP_MODE", "demo")
    out = await ops.process_order_text_service({"replay": make_store()}, "otra cosa")
    assert out is None


# --- robust JSON parsing (ported) ---------------------------------------------------

def test_parse_valid_json_passthrough():
    raw = '{"NUM_ORDER": 1}'
    assert ops._parse_llm_response(raw) == raw


def test_parse_extracts_json_from_chatter_and_fixes_quotes():
    raw = "Claro! Aqui tienes: {'NUM_ORDER': 10417} espero que sirva"
    out = ops._parse_llm_response(raw)
    assert out is not None
    assert json.loads(out)["NUM_ORDER"] == 10417


def test_parse_garbage_returns_none():
    assert ops._parse_llm_response("sin json aqui") is None


# --- real-mode retry x3 backoff 2s*attempt (ported) ---------------------------------

VALID_LLM_JSON = json.dumps({
    "NUM_ORDER": 10417, "CLIENT": "[customer]", "OBSERVACIONES": "",
    "CANTIDAD": [2], "ARTÍCULO": ["taco de 10"], "DESCRIPCIÓN": ["TACO 10 PLASTICO"],
}, ensure_ascii=False)


async def test_real_mode_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr(ops.settings, "APP_MODE", "real")
    calls = {"n": 0}
    sleeps: list[float] = []

    def fake_llm(**kwargs):
        calls["n"] += 1
        return None if calls["n"] < 3 else VALID_LLM_JSON

    monkeypatch.setattr(ops, "get_llm_completion", lambda **kw: fake_llm(**kw))
    monkeypatch.setattr(ops.time, "sleep", lambda s: sleeps.append(s))

    out = await ops.process_order_text_service({}, "transcripcion")
    assert out is not None
    assert calls["n"] == 3
    assert sleeps == [2, 4]   # 2s*attempt backoff
    assert out["num_order"] == "10417"
    assert out["df_order_list_of_dicts"][0]["DESCRIPCIÓN"] == "TACO 10 PLASTICO"


async def test_real_mode_gives_up_after_3_attempts(monkeypatch):
    monkeypatch.setattr(ops.settings, "APP_MODE", "real")
    calls = {"n": 0}

    def fake_llm(**kwargs):
        calls["n"] += 1
        return None

    monkeypatch.setattr(ops, "get_llm_completion", lambda **kw: fake_llm(**kw))
    monkeypatch.setattr(ops.time, "sleep", lambda s: None)
    out = await ops.process_order_text_service({}, "transcripcion")
    assert out is None
    assert calls["n"] == ops.MAX_LLM_RETRIES


async def test_real_mode_rejects_mismatched_lists(monkeypatch):
    monkeypatch.setattr(ops.settings, "APP_MODE", "real")
    bad = json.dumps({"NUM_ORDER": 1, "CANTIDAD": [1, 2], "ARTÍCULO": ["a"],
                      "DESCRIPCIÓN": ["d"]}, ensure_ascii=False)
    monkeypatch.setattr(ops, "get_llm_completion", lambda **kw: bad)
    monkeypatch.setattr(ops.time, "sleep", lambda s: None)
    out = await ops.process_order_text_service({}, "x")
    assert out is None
