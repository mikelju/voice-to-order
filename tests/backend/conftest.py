# tests/backend/conftest.py
"""Backend fixtures. API/flow fixtures need the local DB and skip cleanly without it."""
import os

import pytest
import pytest_asyncio

psycopg = pytest.importorskip("psycopg")

URL = os.environ.get("DATABASE_URL", "postgresql://vto:vto@localhost:5433/vto")


def db_reachable() -> bool:
    try:
        with psycopg.connect(URL, connect_timeout=3):
            return True
    except psycopg.OperationalError:
        return False


@pytest.fixture(scope="session")
def require_db():
    if not db_reachable():
        pytest.skip("local DB not reachable (docker-compose up -d to run these tests)")


@pytest_asyncio.fixture
async def app_started(require_db):
    """The FastAPI app with its lifespan executed (httpx ASGITransport skips lifespan)."""
    from src.backend.app.main import app, lifespan
    async with lifespan(app):
        yield app


@pytest_asyncio.fixture
async def client(app_started):
    from httpx import ASGITransport, AsyncClient
    transport = ASGITransport(app=app_started)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
