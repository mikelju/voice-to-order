# tools/anonlib.py
"""Pure functions shared by the anonymization tools.

Rules (Phase 1 spec, docs/refs/legal-framework-anonymization.md):
- Article ids -> "ART-" + 10 hex of HMAC-SHA256(salt, id). Without the salt the token is
  neither reversible nor dictionary-verifiable.
- Dictated text -> order references to [order-ref] (rule) + term->token replacements
  loaded from a file OUTSIDE the repo (real terms never live here).
- Dates -> month (YYYY-MM).
"""
from __future__ import annotations

import hmac
import hashlib
import re
import unicodedata

ID_TOKEN_RE = re.compile(r"^ART-[0-9a-f]{10}$")
# Order/works references as dictated: "10417", "10 417", "11.393-2", "11C208", "11-3-6-6"
ORDER_REF_RE = re.compile(
    r"\b\d{2}[ .]?\d{3}(?:-\d+)?\b"          # 10417 / 10 417 / 11.393-2
    r"|\b\d{1,2}[A-Z]\d{2,4}\b"              # 11C208
    r"|\b\d{1,2}(?:-\d{1,2}){2,}\b"          # 11-3-6-6
)
MONTH_RE = re.compile(r"^\d{4}-\d{2}$")
# Spanish mobile/landline numbers as found in real admin rows
PHONE_RE = re.compile(r"\b[679]\d{8}\b")

# Uppercase domain vocabulary that is NOT a proper noun (for the review report).
# The dataset's dictated text is Spanish plumbing/HVAC jargon.
DOMAIN_UPPER = {
    "DN", "INOX", "PVC", "PN", "ML", "LT", "CM", "MM", "M", "H", "MH", "HH", "T",
    "DIN", "GALVA", "LATON", "UPN", "IPN", "HEB", "PE", "PP", "EPDM", "NPT", "BSP",
    "AC", "CU", "PEX", "ACS", "KW", "BAR", "UNE", "ISO",
}


def anon_id(real_id: str, salt: str) -> str:
    """Deterministic opaque token for a real article id."""
    if not salt:
        raise ValueError("ANON_SALT is empty: the salt is mandatory")
    digest = hmac.new(salt.encode("utf-8"), real_id.strip().encode("utf-8"),
                      hashlib.sha256).hexdigest()
    return "ART-" + digest[:10]


def load_replacements(path: str) -> list[tuple[str, str]]:
    """Load the term->token mapping from an external file (lines 'term=>token').

    Pairs are returned longest-term-first so that 'Long Company Name' is replaced
    before 'Company'.
    """
    pairs: list[tuple[str, str]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=>" not in line:
                continue
            term, token = line.split("=>", 1)
            term, token = term.strip(), token.strip()
            if term and token:
                pairs.append((term, token))
    pairs.sort(key=lambda p: -len(p[0]))
    return pairs


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))


def sanitize_text(text: str, replacements: list[tuple[str, str]],
                  order_refs: bool = True) -> str:
    """Apply external replacements (case/accent-insensitive), the [phone] rule and,
    optionally, the [order-ref] rule.

    order_refs=False is used for catalog descriptions: their numeric specs (DIN/UNE
    norm numbers, dimensions) must never be mistaken for order references.
    """
    out = text
    for term, token in replacements:
        # exact variant and accent-stripped variant, both case-insensitive
        for variant in {term, _strip_accents(term)}:
            out = re.sub(re.escape(variant), token, out, flags=re.IGNORECASE)
    out = PHONE_RE.sub("[phone]", out)
    if order_refs:
        out = ORDER_REF_RE.sub("[order-ref]", out)
    return out


def to_month(date_str: str) -> str:
    """Reduce a date to YYYY-MM. Empty string when nothing parseable."""
    s = (date_str or "").strip()
    m = re.match(r"^(\d{4})-(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})", s)  # DD/MM/YYYY
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}"
    return ""


def proper_noun_candidates(text: str) -> set[str]:
    """Proper-noun candidates for the manual review report.

    Heuristic: Capitalized words (not at the start of the text) and long ALL-CAPS
    words not in the domain vocabulary. False positives are expected and fine:
    a human decides.
    """
    candidates: set[str] = set()
    words = re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúñ][\wÁÉÍÓÚÑáéíóúñ-]*", text)
    for i, w in enumerate(words):
        bare = w.strip("-")
        if len(bare) < 3 or bare.upper() in DOMAIN_UPPER:
            continue
        if any(ch.isdigit() for ch in bare):   # measures like DN50, M10x25
            continue
        if bare.isupper() and len(bare) >= 4:
            candidates.add(bare)
        elif bare[0].isupper() and bare[1:].islower() and i > 0:
            candidates.add(bare)
    return candidates
