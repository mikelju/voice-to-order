# src/backend/app/core/db.py
"""Async Postgres pool (psycopg3). Replaces the original's Supabase async client.

Note for Windows: psycopg async needs a selector event loop; main.py and the test
conftest set WindowsSelectorEventLoopPolicy before any loop is created.
"""
from __future__ import annotations

from psycopg_pool import AsyncConnectionPool

from .config import settings


def create_pool() -> AsyncConnectionPool:
    return AsyncConnectionPool(settings.DATABASE_URL, min_size=1, max_size=10,
                               open=False, timeout=10)
