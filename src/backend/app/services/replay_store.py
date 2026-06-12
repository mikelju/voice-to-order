# src/backend/app/services/replay_store.py
"""Demo-mode replay store: the 47 validated pairs from data/extraction_pairs.jsonl.

Each pair is {"transcription": str, "expected_items": [{"qty": "24.0", "description": str}]}.
The transcription is the recorded INPUT; expected_items are the human-confirmed catalog
lines (post-matching ground truth). The demo pipeline replays transcription + extraction
from here — vector search then runs for real against the local DB.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ReplayStore:
    def __init__(self, pairs: list[dict]):
        self._pairs = pairs
        self._by_transcription = {p["transcription"]: i for i, p in enumerate(pairs)}

    @classmethod
    def load(cls, data_dir: str | Path) -> "ReplayStore":
        path = Path(data_dir) / "extraction_pairs.jsonl"
        pairs: list[dict] = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    pairs.append(json.loads(line))
        logger.info("Replay store loaded", extra={"pairs": len(pairs)})
        return cls(pairs)

    def __len__(self) -> int:
        return len(self._pairs)

    def get(self, recording_id: int) -> Optional[dict]:
        if 0 <= recording_id < len(self._pairs):
            return self._pairs[recording_id]
        return None

    def id_for_bytes(self, content: bytes) -> int:
        """Deterministic recording selection for an arbitrary demo upload."""
        import hashlib
        if not self._pairs:   # review H4: empty store must not ZeroDivisionError
            raise ValueError("Replay store is empty (data/extraction_pairs.jsonl)")
        digest = hashlib.sha256(content or b"demo").digest()
        return int.from_bytes(digest[:4], "big") % len(self._pairs)

    def find_by_transcription(self, transcription: str) -> Optional[int]:
        return self._by_transcription.get(transcription)

    def listing(self) -> list[dict]:
        return [{"recording_id": i, "transcription": p["transcription"],
                 "n_items": len(p["expected_items"])}
                for i, p in enumerate(self._pairs)]
