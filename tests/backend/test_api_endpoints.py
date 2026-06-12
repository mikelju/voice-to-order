# tests/backend/test_api_endpoints.py
"""API contract tests over the real app (lifespan executed, local DB required).
Demo mode end to end per endpoint. Spec US-1..US-4."""
import pytest


async def test_root_reports_mode(client):
    r = await client.get("/")
    assert r.status_code == 200
    assert "Modo: demo" in r.json()["message"]


async def test_demo_recordings_listing(client):
    r = await client.get("/api/v1/demo/recordings")
    assert r.status_code == 200
    recs = r.json()
    assert len(recs) == 47
    assert {"recording_id", "transcription", "n_items"} <= set(recs[0])


async def test_process_audio_demo_replay_contract(client):
    r = await client.post("/api/v1/orders/process-audio",
                          files={"audio_file": ("demo.wav", b"x", "audio/wav")},
                          data={"recording_id": "0"})
    assert r.status_code == 200
    body = r.json()
    assert body["transcription"].startswith("Pedido [customer]")
    assert body["num_order"] == "10001"
    assert body["planta_name_source"] == "erp"
    assert body["planta_name"] not in (None, "", "Desconocido")
    rows = body["df_order_json"]
    assert rows and {"CANTIDAD", "ARTÍCULO", "DESCRIPCIÓN"} <= set(rows[0])
    assert body["articles_list_original_text"]


async def test_process_audio_not_found_order_warns(client):
    # recording 8 -> num_order 10009 -> simulated ERP not_found
    r = await client.post("/api/v1/orders/process-audio",
                          files={"audio_file": ("demo.wav", b"x", "audio/wav")},
                          data={"recording_id": "8"})
    assert r.status_code == 200
    body = r.json()
    assert body["planta_name_source"] == "llm"
    assert any("no se encontró en el ERP" in w for w in body["warnings"])


async def test_get_planta_contract(client):
    ok = await client.get("/api/v1/orders/get-planta/10001")
    assert ok.status_code == 200 and ok.json()["status"] == "success"
    nf = await client.get("/api/v1/orders/get-planta/10009")
    assert nf.status_code == 404 and nf.json()["status"] == "not_found"
    bad = await client.get("/api/v1/orders/get-planta/abc")
    assert bad.status_code == 400


async def test_search_articles_validates_lengths(client):
    r = await client.post("/api/v1/orders/search-articles", json={
        "articles_list_original_text": ["a", "b"],
        "description_list_for_search": ["solo una"]})
    assert r.status_code == 400


async def test_search_articles_demo_trigram_path(client):
    # No precomputed embeddings yet (Phase 4): the trigram fallback must answer with a
    # real catalog description as the query.
    r = await client.post("/api/v1/orders/search-articles", json={
        "articles_list_original_text": ["tornillo allen métrica 10x25 inox"],
        "description_list_for_search": ["TORNILLO ALLEN M10*25 INOX"],
        "num_opciones_busqueda": 5})
    assert r.status_code == 200
    rows = r.json()["searched_articles"]
    assert rows, "trigram fallback should produce candidates"
    assert any("TORNILLO" in r_["Description"] for r_ in rows)


async def test_catalog_search_manual(client):
    r = await client.get("/api/v1/catalog/search", params={"query": "tornillo allen"})
    assert r.status_code == 200
    rows = r.json()
    assert rows and all({"id_articulo", "articulo"} <= set(x) for x in rows)
    assert len(rows) <= 50
    short = await client.get("/api/v1/catalog/search", params={"query": "ab"})
    assert short.status_code == 422   # min_length=3


async def test_finalize_contract(client):
    r = await client.post("/api/v1/orders/finalize", json={
        "selected_items": [
            {"original_article_text": "taco de 10",
             "selected_catalog_description": "TACO 10 PLASTICO 4 SEGMENTOS",
             "selected_catalog_id": "ART-fb9d671f81", "quantity": 2.5}],
        "num_order": "10001", "planta_name": "Planta Norte"})
    assert r.status_code == 200
    body = r.json()
    assert body["final_order_items"][0]["Uds"] == 2.5
    assert body["final_order_items"][0]["Descripción"]
    assert body["has_duplicates_or_issues"] is False


async def test_demo_recordings_404_in_real_mode(client, monkeypatch):
    from src.backend.app.routers import demo_router
    monkeypatch.setattr(demo_router.settings, "APP_MODE", "real")
    r = await client.get("/api/v1/demo/recordings")
    assert r.status_code == 404


async def test_send_without_num_order_omits_erp(client, tmp_path, monkeypatch):
    from src.backend.app.core.config import settings
    monkeypatch.setattr(settings, "SIMULATE_FAILURE", "")
    monkeypatch.setattr(settings, "OUTBOX_DIR", str(tmp_path / "outbox"))
    monkeypatch.setattr(settings, "ERP_DIR", str(tmp_path / "erp"))
    r = await client.post("/api/v1/orders/send", json={
        "final_order_items": [{"Uds": 1.0, "Ids": "ART-0123456789",
                               "Descripción": "X"}],
        "items_for_history": [], "num_order": None, "planta_name": "P"})
    assert r.status_code == 200
    body = r.json()
    assert body["erp_update_status"] == "omitido"
    assert body["order_sent_status"] == "enviado"
    assert not list((tmp_path / "erp").glob("*.json"))


async def test_send_only_sentinel_items_omits_erp(client, tmp_path, monkeypatch):
    from src.backend.app.core.config import settings
    monkeypatch.setattr(settings, "SIMULATE_FAILURE", "")
    monkeypatch.setattr(settings, "OUTBOX_DIR", str(tmp_path / "outbox"))
    monkeypatch.setattr(settings, "ERP_DIR", str(tmp_path / "erp"))
    r = await client.post("/api/v1/orders/send", json={
        "final_order_items": [{"Uds": 1.0, "Ids": "HERRAMIENTA",
                               "Descripción": "taladro"}],
        "items_for_history": [], "num_order": "10001", "planta_name": "P"})
    assert r.status_code == 200
    assert r.json()["erp_update_status"] == "omitido"


def test_semaphore_constants_are_the_original_values():
    from src.backend.app.services import search_service as svc
    assert svc.LLM_CONCURRENCY_LIMIT == 10
    assert svc.DB_CONCURRENCY_LIMIT == 10
