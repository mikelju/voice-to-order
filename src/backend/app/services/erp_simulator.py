# src/backend/app/services/erp_simulator.py
"""Simulated ERP channel.

Replaces the original's ErpApiClient (real ERP API behind a VPC; see the case study).
Same interface and payload shape; deterministic local behavior:

- get_client_data_by_order_id: order ids ending in 9 -> ("not_found", None) so the
  warning path is exercised; anything else resolves a fictional plant name.
- send_order_to_erp: writes the original's exact payload
  {"IdParte": int, "Lineas": [{"IdArticulo", "Cantidad"}]} to .tmp/erp/ and returns
  (True, message). Chaos: "erp" in SIMULATE_FAILURE -> (False, message) without writing.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

from ..core.config import settings

logger = logging.getLogger(__name__)

PLANT_NAMES = ["Planta Norte", "Planta Sur", "Nave Central", "Obra Rio", "Planta Este"]


class ErpSimulator:
    async def get_client_data_by_order_id(self, order_id: str
                                          ) -> tuple[str, Optional[dict]]:
        try:
            n = int(order_id)
        except (TypeError, ValueError):
            return "error", None
        if n % 10 == 9:
            return "not_found", None
        return "success", {"Planta": PLANT_NAMES[n % len(PLANT_NAMES)]}

    async def send_order_to_erp(self, order_id: str, items: list[dict]
                                ) -> tuple[bool, str]:
        if "erp" in settings.SIMULATE_FAILURE:
            logger.warning("Chaos: simulated ERP failure (SIMULATE_FAILURE)")
            return False, "Fallo simulado del ERP (SIMULATE_FAILURE)"
        try:
            lineas = [{"IdArticulo": item["Ids"], "Cantidad": item["Uds"]}
                      for item in items]
            payload = {"IdParte": int(order_id), "Lineas": lineas}
        except (KeyError, TypeError, ValueError) as exc:
            return False, f"Payload de ERP inválido: {exc}"
        try:
            out_dir = Path(settings.ERP_DIR)
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / f"order_{order_id}_{int(time.time())}.json"
            out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                                encoding="utf-8")
        except OSError as exc:   # review H6: channel failure -> (False, msg), never 500
            logger.exception("Simulated ERP write failed")
            return False, f"Fallo del canal ERP simulado: {exc}"
        logger.info("Simulated ERP delivery", extra={"file": str(out_file)})
        return True, f"Pedido registrado en el ERP simulado ({out_file.name})"


erp_api_client = ErpSimulator()
