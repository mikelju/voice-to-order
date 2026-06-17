# src/backend/app/main.py
"""Voice-to-Order API entry point.

Run from the repo root:
    uvicorn src.backend.app.main:app --reload

Lifespan (ported design): clients live in app.state.clients; an init failure is logged
as critical but the app starts anyway (services then fail with clear 500s).
"""
from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

# psycopg async needs a selector loop on Windows (Proactor lacks add_reader). Set the
# policy at import time so `uvicorn src.backend.app.main:app` works out of the box.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .core.db import create_pool
from .core.logging_config import setup_logging
from .routers import catalog_router, demo_router, order_processing_router
from .services.embedding_service import EmbeddingService
from .services.replay_store import ReplayStore
from .services.search_utils import PgVectorSearcher

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.LOG_LEVEL)
    app.state.clients = {}
    pool = None
    try:
        pool = create_pool()
        await pool.open()
        app.state.clients["pool"] = pool
        embedder = EmbeddingService(pool)
        app.state.clients["embedder"] = embedder
        app.state.clients["searcher"] = PgVectorSearcher(pool, embedder)
        if settings.APP_MODE == "demo":
            app.state.clients["replay"] = ReplayStore.load(settings.DATA_DIR)
        logger.info("Lifespan init done", extra={"mode": settings.APP_MODE})
    except Exception:
        # ported behavior: the app starts anyway; endpoints fail with clear 500s
        logging.critical("Client initialization failed", exc_info=True)
    yield
    if pool is not None:
        await pool.close()


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan,
              openapi_url=f"{settings.API_V1_STR}/openapi.json")

# CORS (ported dev fallback: Vite port-retry range 5173-5180)
origins = ([f"http://localhost:{port}" for port in range(5173, 5181)]
           + [f"http://127.0.0.1:{port}" for port in range(5173, 5181)])
# SEC-003 (audit 2026-06-17): the app uses no cookies/auth, so credentials are never
# sent; allow_credentials stays False to keep the CORS surface minimal.
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False,
                   allow_methods=["*"], allow_headers=["*"])


@app.get("/")
async def root():
    return {"message": f"Bienvenido a {settings.APP_NAME} v1. "
                       f"Modo: {settings.APP_MODE}"}


app.include_router(order_processing_router.router, prefix=settings.API_V1_STR,
                   tags=["Order Processing"])
app.include_router(catalog_router.router, prefix=settings.API_V1_STR, tags=["Catalog"])
app.include_router(demo_router.router, prefix=settings.API_V1_STR, tags=["Demo"])
