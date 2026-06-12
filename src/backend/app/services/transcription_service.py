# src/backend/app/services/transcription_service.py
"""Step 2 — Transcribe.

demo mode: replay of a recorded (anonymized) transcription from the ReplayStore;
selection by explicit recording_id, or deterministically by hash of the upload bytes.

real mode: whisper-1 via the OpenAI client in a worker thread (ported: tempfile dance,
None on any failure).
"""
from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from typing import Any, Optional

from ..core.config import settings

logger = logging.getLogger(__name__)


async def transcribe_audio_service(clients: dict[str, Any], audio_file_content: bytes,
                                   filename: str,
                                   recording_id: Optional[int] = None
                                   ) -> Optional[tuple[str, Optional[int]]]:
    """Return (transcription, recording_id or None). None on failure."""
    if settings.APP_MODE == "demo":
        store = clients.get("replay")
        if store is None:
            logger.error("Demo mode without replay store")
            return None
        rid = recording_id if recording_id is not None \
            else store.id_for_bytes(audio_file_content)
        pair = store.get(rid)
        if pair is None:
            logger.error("Unknown recording_id %s", rid)
            return None
        logger.info("Demo replay transcription", extra={"recording_id": rid})
        return pair["transcription"], rid

    text = await _transcribe_real(audio_file_content, filename)
    return None if text is None else (text, None)


async def _transcribe_real(audio_file_content: bytes, filename: str) -> Optional[str]:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        suffix = os.path.splitext(filename or "")[1] or ".tmp"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, mode="wb")
        try:
            tmp.write(audio_file_content)
            tmp.close()

            def _transcribe_sync() -> str:
                with open(tmp.name, "rb") as f:
                    result = client.audio.transcriptions.create(model="whisper-1", file=f)
                return result.text

            text = await asyncio.to_thread(_transcribe_sync)
            logger.info("Whisper transcription ok",
                        extra={"chars": len(text), "filename": filename})
            return text
        finally:
            try:
                os.remove(tmp.name)
            except OSError:
                logger.warning("Could not remove temp audio file %s", tmp.name)
    except Exception:
        logger.exception("Transcription failed for %s", filename)
        return None
