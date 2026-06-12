# tests/backend/test_demo_flow.py
"""End-to-end demo flow over the API: process-audio -> search-articles -> finalize ->
send (3 status lights + memory upsert), plus a chaos run (SIMULATE_FAILURE=erp).
Spec: the phase goal — the 7-step pipeline runs locally with no API keys."""
import base64

import psycopg
import pytest

from tests.backend.conftest import URL

RID = 0   # recording 0 -> num_order 10001 (resolvable by the simulated ERP)


async def run_until_finalize(client):
    r1 = await client.post("/api/v1/orders/process-audio",
                           files={"audio_file": ("demo.wav", b"x", "audio/wav")},
                           data={"recording_id": str(RID)})
    assert r1.status_code == 200, r1.text
    p = r1.json()

    r2 = await client.post("/api/v1/orders/search-articles", json={
        "articles_list_original_text": p["articles_list_original_text"],
        "description_list_for_search": [row["DESCRIPCIÓN"]
                                        for row in p["df_order_json"]],
        "num_opciones_busqueda": 5})
    assert r2.status_code == 200, r2.text
    candidates = r2.json()["searched_articles"]
    assert candidates, "demo search must produce candidates (trigram or vector)"

    # pick the top candidate per article (what the UI preselects)
    by_article: dict = {}
    for row in candidates:
        by_article.setdefault(row["Article"], row)
    selected = [{"original_article_text": art,
                 "selected_catalog_description": row["Description"],
                 "selected_catalog_id": row["Ids"],
                 "quantity": qty}
                for (art, row), qty in zip(
                    by_article.items(),
                    [r["CANTIDAD"] for r in p["df_order_json"]])]

    r3 = await client.post("/api/v1/orders/finalize", json={
        "selected_items": selected, "num_order": p["num_order"],
        "planta_name": p["planta_name"]})
    assert r3.status_code == 200, r3.text
    return p, by_article, r3.json()


async def test_full_demo_flow_green_path(client, tmp_path, monkeypatch):
    from src.backend.app.core.config import settings
    monkeypatch.setattr(settings, "SIMULATE_FAILURE", "")
    monkeypatch.setattr(settings, "OUTBOX_DIR", str(tmp_path / "outbox"))
    monkeypatch.setattr(settings, "ERP_DIR", str(tmp_path / "erp"))

    p, by_article, finalized = await run_until_finalize(client)

    items_for_history = [{"Ids": row["Ids"], "Artículo": art,
                          "Descripción": row["Description"]}
                         for art, row in by_article.items()]
    r4 = await client.post("/api/v1/orders/send", json={
        "final_order_items": finalized["final_order_items"],
        "items_for_history": items_for_history,
        "num_order": p["num_order"], "planta_name": p["planta_name"],
        "plazo": "2026-06-15", "observaciones": "pedido de prueba e2e",
        "enviar_a_obra": True, "solo_imputar": False})
    assert r4.status_code == 200, r4.text
    body = r4.json()

    # the three status lights
    assert body["order_sent_status"] == "enviado"
    assert body["erp_update_status"] == "exito"
    assert body["historical_update_status"] == "success"
    assert body["error_details"] is None
    # real PDF
    pdf = base64.b64decode(body["pdf_download_data"]["b64_pdf"])
    assert pdf[:5] == b"%PDF-"
    # simulated channels wrote their artifacts
    assert list((tmp_path / "outbox").glob("email_*.json"))
    assert list((tmp_path / "erp").glob("order_10001_*.json"))

    # the learning loop wrote memory rows (cleanup after assert)
    with psycopg.connect(URL) as conn:
        n = conn.execute(
            "SELECT count(*) FROM historico_pedidos WHERE last_used_month = "
            "to_char(now(), 'YYYY-MM')").fetchone()[0]
        assert n >= 1
        conn.execute(
            "DELETE FROM historico_embeddings WHERE historico_id IN ("
            "SELECT id FROM historico_pedidos WHERE last_used_month = "
            "to_char(now(), 'YYYY-MM') AND frequency = 1)")
        conn.execute(
            "DELETE FROM historico_pedidos WHERE last_used_month = "
            "to_char(now(), 'YYYY-MM') AND frequency = 1")


async def test_full_demo_flow_chaos_erp(client, tmp_path, monkeypatch):
    """Run B of the case study: ERP fails (injected), email+PDF deliver anyway."""
    from src.backend.app.core.config import settings
    monkeypatch.setattr(settings, "SIMULATE_FAILURE", "erp")
    monkeypatch.setattr(settings, "OUTBOX_DIR", str(tmp_path / "outbox"))
    monkeypatch.setattr(settings, "ERP_DIR", str(tmp_path / "erp"))

    p, by_article, finalized = await run_until_finalize(client)
    r4 = await client.post("/api/v1/orders/send", json={
        "final_order_items": finalized["final_order_items"],
        "items_for_history": [],
        "num_order": p["num_order"], "planta_name": p["planta_name"]})
    assert r4.status_code == 200
    body = r4.json()

    assert body["order_sent_status"] == "fallido"           # ERP is critical
    assert body["erp_update_status"] == "fallido"
    assert "ERP" in (body["error_details"] or "")
    assert body["pdf_download_data"] is not None            # PDF still returned
    assert list((tmp_path / "outbox").glob("email_*.json"))  # email still delivered
    assert not list((tmp_path / "erp").glob("*.json"))       # nothing reached the ERP
    assert body["message"].startswith("Error crítico")
