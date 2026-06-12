# tests/db/test_historical_upsert.py
"""The learning loop: upsert_historico_with_status (frequency++/is_new) and the service
around it (normalization, sentinel skip, chaos). Spec US-3."""
import asyncio
import os
import sys

import pytest
import pytest_asyncio

psycopg = pytest.importorskip("psycopg")
from psycopg_pool import AsyncConnectionPool  # noqa: E402

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

URL = os.environ.get("DATABASE_URL", "postgresql://vto:vto@localhost:5433/vto")
MARK = "zz prueba upsert fase3"


@pytest_asyncio.fixture
async def pool():
    try:
        with psycopg.connect(URL, connect_timeout=3):
            pass
    except psycopg.OperationalError:
        pytest.skip("local DB not reachable (docker-compose up -d to run these tests)")
    p = AsyncConnectionPool(URL, min_size=1, max_size=4, open=False)
    await p.open()
    yield p
    async with p.connection() as conn:
        await conn.execute(
            "DELETE FROM historico_pedidos WHERE user_text LIKE %s", (MARK + "%",))
    await p.close()


async def any_catalog_id(pool):
    async with pool.connection() as conn:
        row = await (await conn.execute(
            "SELECT id_articulo FROM catalogo LIMIT 1")).fetchone()
    return row[0]


async def test_upsert_new_then_frequency_increment(pool):
    art = await any_catalog_id(pool)
    async with pool.connection() as conn:
        first = await (await conn.execute(
            "SELECT historico_id, is_new FROM upsert_historico_with_status"
            "(%s, 'DESCRIPCION DE PRUEBA', %s, '2026-06')",
            (MARK + " uno", art))).fetchone()
        second = await (await conn.execute(
            "SELECT historico_id, is_new FROM upsert_historico_with_status"
            "(%s, 'DESCRIPCION DE PRUEBA', %s, '2026-07')",
            (MARK + " uno", art))).fetchone()
        freq, month = await (await conn.execute(
            "SELECT frequency, last_used_month FROM historico_pedidos WHERE id = %s",
            (first[0],))).fetchone()
    assert first[1] is True            # new row
    assert second[0] == first[0] and second[1] is False
    assert freq == 2 and month == "2026-07"


async def test_service_normalizes_and_skips_sentinel(pool, monkeypatch):
    from src.backend.app.services import historical_data_service as hds
    monkeypatch.setattr(hds.settings, "APP_MODE", "demo")
    monkeypatch.setattr(hds.settings, "SIMULATE_FAILURE", "")
    art = await any_catalog_id(pool)
    items = [
        {"Ids": art, "Artículo": f"2 {MARK.upper()} Códos", "Descripción": "DESC X"},
        {"Ids": art, "Artículo": "lo que sea", "Descripción": "--- SIN OPCIONES ---"},
    ]
    out = await hds.update_historical_data_service({"pool": pool}, items, "10001")
    assert out["status"] == "success"
    async with pool.connection() as conn:
        row = await (await conn.execute(
            "SELECT user_text FROM historico_pedidos WHERE catalog_description = "
            "'DESC X' AND user_text LIKE %s", (MARK + "%",))).fetchone()
    # leading quantity stripped, accents removed, lowercase (ported normalize_text)
    assert row[0] == f"{MARK} codos"


async def test_service_chaos_raises(monkeypatch):
    from src.backend.app.services import historical_data_service as hds
    monkeypatch.setattr(hds.settings, "SIMULATE_FAILURE", "history")
    with pytest.raises(ConnectionError):
        await hds.update_historical_data_service({}, [], "1")
