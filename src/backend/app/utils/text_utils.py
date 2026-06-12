# src/backend/app/utils/text_utils.py
"""Text normalization for the learned memory, ported from the original."""
from __future__ import annotations

import re
import unicodedata

_LEADING_QTY_RE = re.compile(
    r"^(?:\d+|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)\s+",
    re.IGNORECASE,
)


def normalize_text(text: str) -> str:
    """Strip leading quantities, accents and non-alphanumerics; lowercase."""
    out = _LEADING_QTY_RE.sub("", text or "")
    out = "".join(c for c in unicodedata.normalize("NFKD", out)
                  if not unicodedata.combining(c))
    out = out.lower()
    out = re.sub(r"[^a-z0-9\s]", "", out)
    return out.strip()
