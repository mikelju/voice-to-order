# src/backend/app/services/email_simulator.py
"""Simulated email channel.

Replaces the original's O365 EmailSender. Ported logic that matters and is demonstrable:
- recipient selection by the workday cutoff (Mon-Fri and hour < 14h -> workday list,
  otherwise off-hours list; any failure -> fallback recipient);
- retry x3 with attempt*2 backoff on (simulated) connection errors.

Delivery = a JSON message written to .tmp/outbox/. Chaos: "email" in SIMULATE_FAILURE
raises ConnectionError on every attempt, so the retry path runs and ultimately fails.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ..core.config import settings

logger = logging.getLogger(__name__)

RECIPIENTS_WORKDAY = ["oficina@example.com", "compras@example.com"]
RECIPIENTS_OFFHOURS = ["guardia@example.com"]
FALLBACK_RECIPIENT = "fallback@example.com"

MAX_RETRIES = 3


def select_recipients(now: datetime | None = None) -> list[str]:
    """Ported: Mon-Fri before the cutoff -> workday list; otherwise off-hours."""
    try:
        tz = ZoneInfo(settings.TIMEZONE)
        current = now or datetime.now(tz)
        is_workday = 0 <= current.weekday() <= 4
        is_workhours = current.hour < settings.WORKDAY_CUTOFF_HOUR
        recipients = RECIPIENTS_WORKDAY if (is_workday and is_workhours) \
            else RECIPIENTS_OFFHOURS
        if not recipients:
            raise ValueError("Empty recipient list")
        return recipients
    except Exception:
        return [FALLBACK_RECIPIENT]


class EmailSimulator:
    async def send_email_async(self, pdf_path: str, order_data: dict,
                               sender_email: str) -> bool:
        recipients = select_recipients()
        solo_imputar = order_data.get("solo_imputar", False)
        subject = (f"{'Imputar' if solo_imputar else 'Pedido'} "
                   f"{order_data.get('planta_name') or 'S/P'} "
                   f"{order_data.get('num_order') or 'S/N'} "
                   f"Plazo: {order_data.get('plazo') or '-'}")
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                sent = await asyncio.to_thread(
                    self._send_sync, recipients, subject, pdf_path, order_data,
                    sender_email)
                if sent:
                    logger.info("[OK] Simulated email delivered (attempt %s)", attempt)
                    return True
                logger.warning("Email send returned False (attempt %s/%s)",
                               attempt, MAX_RETRIES)
            except (ConnectionError, OSError) as exc:
                logger.warning("Connection error sending email (attempt %s/%s): %s",
                               attempt, MAX_RETRIES, exc)
                if attempt < MAX_RETRIES:
                    wait = attempt * 2   # ported backoff: 2s, 4s
                    await asyncio.sleep(wait)
                else:
                    return False
        return False

    def _send_sync(self, recipients: list[str], subject: str, pdf_path: str,
                   order_data: dict, sender_email: str) -> bool:
        if "email" in settings.SIMULATE_FAILURE:
            raise ConnectionError("Fallo simulado del email (SIMULATE_FAILURE)")
        out_dir = Path(settings.OUTBOX_DIR)
        out_dir.mkdir(parents=True, exist_ok=True)
        message = {
            "from": sender_email,
            "to": recipients,
            "subject": subject,
            "body": ("Adjunto pedido de material. "
                     f"Observaciones: {order_data.get('observaciones') or '-'}"),
            "attachment": Path(pdf_path).name,
        }
        out_file = out_dir / f"email_{int(time.time() * 1000)}.json"
        out_file.write_text(json.dumps(message, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        return True


email_sender_instance = EmailSimulator()
