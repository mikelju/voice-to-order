# src/backend/app/routers/demo_router.py
"""Demo-only endpoints (replica addition): list the recorded orders so the UI can offer
a picker. 404 in real mode."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Request

from ..core.config import settings
from ..models.order_models import DemoRecording

router = APIRouter(prefix="/demo")


@router.get("/recordings", response_model=List[DemoRecording])
async def list_recordings(request: Request):
    if settings.APP_MODE != "demo":
        raise HTTPException(status_code=404, detail="Solo disponible en modo demo.")
    store = request.app.state.clients.get("replay")
    if store is None:
        raise HTTPException(status_code=500, detail="Replay store no disponible.")
    return [DemoRecording(**rec) for rec in store.listing()]
