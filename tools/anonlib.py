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
# Spanish mobile/landline numbers as found in real admin rows. fix-1: besides 9
# contiguous digits, capture the common spaced/dotted groupings (3-3-3 and 3-2-2-2);
# over-matching a technical spec is acceptable in exchange for not leaking a phone.
PHONE_RE = re.compile(
    r"\b[679]\d{2}[ .]?\d{3}[ .]?\d{3}\b"        # 696719831 / 638 361 923 / 696.719.831
    r"|\b[679]\d{2}[ .]?\d{2}[ .]?\d{2}[ .]?\d{2}\b"  # 620 51 55 59
)
# fix-1: structural rule for catalog admin rows starting with "CONTACTO:". In those
# rows every capitalized/name-like word run is a person, role or company name (the
# operational text "llamar en horario..." is lowercase) -> tokenize them all.
CONTACT_START_RE = re.compile(r"^\s*CONTACTO\b:?\s*", re.IGNORECASE)
NAME_RUN_RE = re.compile(
    r"\b[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ]*"
    r"(?:[ \-]+(?:de|del|la|el|y|[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ]*))*\b"
)

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
    m = CONTACT_START_RE.match(out)
    if m:
        rest = NAME_RUN_RE.sub(_contact_name_repl, out[m.end():])
        rest = re.sub(r"\[person\](?:[ ,\-]+\[person\])+", "[person]", rest)
        out = "CONTACTO: " + rest
    if order_refs:
        out = ORDER_REF_RE.sub("[order-ref]", out)
    return out


_NAME_CONNECTORS = {"de", "del", "la", "el", "y"}


def _contact_name_repl(m: "re.Match[str]") -> str:
    """Replace a name-like run in an admin row, except pure domain vocabulary
    (technical norms like 'DIN' must survive)."""
    words = re.split(r"[ \-]+", m.group(0))
    if all(w.upper() in DOMAIN_UPPER or w.lower() in _NAME_CONNECTORS for w in words if w):
        return m.group(0)
    return "[person]"


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
