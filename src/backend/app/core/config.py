# src/backend/app/core/config.py
"""Application settings (pydantic-settings), loaded from .env at the repo root.

Ported from the original's app/core/config.py. Replica differences:
- APP_MODE=demo|real replaces the original's implicit "always live" behavior.
- Plain local Postgres (DATABASE_URL) instead of Supabase URL/keys.
- Simulated delivery channels need no O365/ERP credentials.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Mode ------------------------------------------------------------------
    APP_MODE: str = "demo"                 # demo | real
    APP_NAME: str = "Voice-to-Order API"
    API_V1_STR: str = "/api/v1"
    LOG_LEVEL: str = "INFO"                # deviation: the original hardcoded WARNING

    # Database ----------------------------------------------------------------
    DATABASE_URL: str = "postgresql://vto:vto@localhost:5433/vto"

    # Models (real mode; names route the provider in llm_wrapper) -------------
    OPENAI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    PROCESSING_LLM_MODEL: str = "gemini-2.5-flash"
    RANKING_LLM_MODEL: str = "gemini-2.5-flash"
    EMBEDDINGS_MODEL_NAME: str = "text-embedding-3-small"
    EMBEDDINGS_DIM: int = 256              # Phase-2 schema contract (vector(256))

    # Delivery (simulated channels) -------------------------------------------
    WORKDAY_CUTOFF_HOUR: int = 14          # original: recipients switch at 14h
    TIMEZONE: str = "Europe/Madrid"
    SIMULATE_FAILURE: str = ""             # chaos: substring match on erp,email,history
    OUTBOX_DIR: str = ".tmp/outbox"        # simulated email channel
    ERP_DIR: str = ".tmp/erp"              # simulated ERP channel

    # Data ---------------------------------------------------------------------
    DATA_DIR: str = "data"                 # replay pairs live here

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
