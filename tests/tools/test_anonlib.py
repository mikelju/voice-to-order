# tests/tools/test_anonlib.py
"""Tests for the pure anonymization functions. Synthetic fixtures ONLY."""
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from anonlib import (  # noqa: E402
    ID_TOKEN_RE,
    anon_id,
    load_replacements,
    proper_noun_candidates,
    sanitize_text,
    to_month,
)


# --- anon_id (HU-1: deterministic, format, irreversible without the salt) ---

def test_anon_id_format():
    assert ID_TOKEN_RE.match(anon_id("AB12345678", "salt-test"))


def test_anon_id_deterministic_and_salt_dependent():
    a = anon_id("AB12345678", "salt-A")
    assert a == anon_id("AB12345678", "salt-A")          # same id+salt -> same token
    assert a != anon_id("AB12345678", "salt-B")          # other salt -> other token
    assert a != anon_id("AB12345679", "salt-A")          # other id -> other token


def test_anon_id_strips_whitespace():
    assert anon_id(" X1 ", "s") == anon_id("X1", "s")


def test_anon_id_requires_salt():
    with pytest.raises(ValueError):
        anon_id("X1", "")


# --- sanitize_text (HU-1: external terms + [order-ref]) ---

REPL = [("Empresa Ficticia", "[customer]"), ("ObraDemo", "[site]")]


def test_sanitize_replaces_terms_case_insensitive():
    out = sanitize_text("Pedido EMPRESA ficticia para obrademo", REPL)
    assert "[customer]" in out and "[site]" in out
    assert "ficticia" not in out.lower().replace("[customer]", "")


def test_sanitize_replaces_accent_variants():
    repl = [("Pamplónica", "[customer]")]
    assert sanitize_text("pedido pamplonica urgente", repl) == "pedido [customer] urgente"


def test_sanitize_order_refs():
    out = sanitize_text("Pedido 10417, obra 11.393-2, vale", [])
    assert "10417" not in out and "11.393" not in out
    assert out.count("[order-ref]") == 2


def test_sanitize_order_refs_letter_and_dash_styles():
    out = sanitize_text("obra 11C208 y parte 11-3-6-6 listos", [])
    assert "11C208" not in out and "11-3-6-6" not in out
    assert out.count("[order-ref]") == 2


def test_sanitize_keeps_measures():
    # typical dictated measures must NOT be touched
    s = "24 tornillos allen metrica 10x25 inox DN50 M10"
    assert sanitize_text(s, []) == s


def test_sanitize_spaced_phones():
    # fix-1: spaced/dotted phone groupings must be tokenized too
    cases = [
        "CONTACTO: ALGUIEN 620 51 55 59  -llamar en horario-",
        "aviso al 638 361 923 antes de entregar",
        "telefono 696.719.831 puesto",
        "movil 671234567 directo",
    ]
    for s in cases:
        out = sanitize_text(s, [])
        assert "[phone]" in out, s
        assert not re.search(r"[679]\d{2}[ .]?\d{2,3}[ .]?\d{2}[ .]?\d{0,3}\d", out), out


def test_sanitize_keeps_technical_numbers_not_phones():
    # DIN/UNE specs and measures must survive the extended phone rule
    s = "JUNTA DIN DN50 130 grados 10x25 M10 PN30 UNE 19702"
    assert sanitize_text(s, [], order_refs=False) == s


def test_sanitize_contact_rows_strip_names():
    # fix-1: any name after CONTACTO is structurally replaced by [person]
    out = sanitize_text(
        "CONTACTO: NOMBRE APELLIDO - 628 32 86 21  -llamar en horario de 7:00h a 15:00h-",
        [], order_refs=False)
    assert "NOMBRE" not in out and "APELLIDO" not in out
    assert "[person]" in out and "[phone]" in out


def test_sanitize_contact_rows_stop_at_existing_tokens():
    out = sanitize_text("CONTACTO: NOMBRE [customer] 620 51 55 59", [], order_refs=False)
    assert "NOMBRE" not in out
    assert "[customer]" in out and "[person]" in out and "[phone]" in out


def test_sanitize_contact_rows_name_after_phone():
    # fix-1: name-like runs anywhere in an admin row (e.g. role + village in parens)
    out = sanitize_text("CONTACTO: NOMBRE 620 51 55 59 (Cargo Valle de Sitio)",
                        [], order_refs=False)
    assert "Cargo" not in out and "Valle" not in out and "Sitio" not in out
    assert "([person])" in out


def test_sanitize_contact_only_for_admin_rows():
    # technical rows containing the word CONTACTO must NOT be touched
    s = "ADHESIVO DE CONTACTO 5L"
    assert sanitize_text(s, [], order_refs=False) == s


def test_load_replacements_longest_first(tmp_path):
    f = tmp_path / "repl.txt"
    f.write_text("# comment\nAcme Demo=>[customer]\nAcme=>[customer]\n", encoding="utf-8")
    pairs = load_replacements(str(f))
    assert pairs[0][0] == "Acme Demo"


# --- to_month (HU-1: dates -> month) ---

@pytest.mark.parametrize("raw,expected", [
    ("2025-03-18 05:30:37+00", "2025-03"),
    ("2025-03-18", "2025-03"),
    ("18/03/2025", "2025-03"),
    ("", ""),
    ("n/a", ""),
])
def test_to_month(raw, expected):
    assert to_month(raw) == expected


# --- proper_noun_candidates (HU-1: manual review report) ---

def test_candidates_flags_capitalized_and_allcaps():
    c = proper_noun_candidates("Pedido para Vexalia, 4 codos QXZR inox")
    assert "Vexalia" in c and "QXZR" in c


def test_candidates_ignores_domain_vocab_and_sentence_start():
    c = proper_noun_candidates("Pedido de 4 codos INOX DN50 y tubo GALVA")
    assert c == set()
