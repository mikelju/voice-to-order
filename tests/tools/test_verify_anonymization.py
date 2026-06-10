# tests/tools/test_verify_anonymization.py
"""Tests for the verification gate, with synthetic fixtures."""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "tools" / "verify_anonymization.py"

GOOD_CATALOG = ("id_articulo,articulo,ultima_compra_mes\n"
                "ART-0123456789,VALVULA BOLA 1/2 LATON,2025-03\n"
                "ART-abcdef0123,CODO INOX DN50,\n")
GOOD_HISTORICAL = ("user_text,catalog_description,id_articulo,frequency,last_used_month\n"
                   "valvula de [customer],VALVULA BOLA 1/2 LATON,ART-0123456789,2,2025-03\n")
GOOD_PAIR = json.dumps({"transcription": "Pedido [customer] [order-ref], 2 valvulas",
                        "expected_items": [{"qty": "2.0", "description": "VALVULA BOLA"}]})


def write_data(d: Path, catalog=GOOD_CATALOG, historical=GOOD_HISTORICAL, pair=GOOD_PAIR):
    d.mkdir(parents=True, exist_ok=True)
    (d / "catalog.csv").write_text(catalog, encoding="utf-8")
    (d / "historical.csv").write_text(historical, encoding="utf-8")
    (d / "extraction_pairs.jsonl").write_text(pair + "\n", encoding="utf-8")


def run(data_dir: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(TOOL), str(data_dir), *extra],
                          capture_output=True, text=True)


def test_green_dataset_passes(tmp_path):
    write_data(tmp_path / "data")
    proc = run(tmp_path / "data")
    assert proc.returncode == 0, proc.stdout
    assert "0 FAIL" in proc.stdout


def test_bad_id_format_fails(tmp_path):
    write_data(tmp_path / "data", catalog=GOOD_CATALOG.replace("ART-abcdef0123", "AB222"))
    proc = run(tmp_path / "data")
    assert proc.returncode == 1
    assert "ART-<10hex>" in proc.stdout


def test_forbidden_column_fails(tmp_path):
    bad = ("id_articulo,articulo,ultima_compra_mes,UltimoProveedor\n"
           "ART-0123456789,X,2025-03,Prov SA\n")
    write_data(tmp_path / "data", catalog=bad)
    assert run(tmp_path / "data").returncode == 1


def test_orphan_fk_fails(tmp_path):
    bad = GOOD_HISTORICAL.replace("ART-0123456789", "ART-ffffffffff")
    write_data(tmp_path / "data", historical=bad)
    proc = run(tmp_path / "data")
    assert proc.returncode == 1
    assert "referential integrity" in proc.stdout


def test_order_ref_leak_fails(tmp_path):
    bad = GOOD_HISTORICAL.replace("[customer]", "[customer] pedido 10417")
    write_data(tmp_path / "data", historical=bad)
    assert run(tmp_path / "data").returncode == 1


def test_secret_leak_fails(tmp_path):
    write_data(tmp_path / "data")
    # built at runtime so the repo-wide secret sweep never matches this test file itself
    fake_key = "sk-" + "A" * 24 + "1234"
    (tmp_path / "data" / "notes.txt").write_text(f"key={fake_key}\n", encoding="utf-8")
    proc = run(tmp_path / "data")
    assert proc.returncode == 1
    assert "no secrets" in proc.stdout


def test_phone_leak_fails(tmp_path):
    write_data(tmp_path / "data",
               historical=GOOD_HISTORICAL.replace("[customer]", "[customer] 680559813"))
    proc = run(tmp_path / "data")
    assert proc.returncode == 1
    assert "no phone numbers" in proc.stdout


def test_terms_sweep_finds_real_term(tmp_path):
    write_data(tmp_path / "data",
               historical=GOOD_HISTORICAL.replace("[customer]", "SecretClientName"))
    terms = tmp_path / "terms.txt"
    terms.write_text("SecretClientName\n", encoding="utf-8")
    proc = run(tmp_path / "data", "--terms", str(terms))
    assert proc.returncode == 1
    assert "real-terms sweep" in proc.stdout


def test_terms_sweep_clean_passes(tmp_path):
    write_data(tmp_path / "data")
    terms = tmp_path / "terms.txt"
    terms.write_text("SecretClientName\nOtherCompany\n", encoding="utf-8")
    assert run(tmp_path / "data", "--terms", str(terms)).returncode == 0
