# tests/tools/test_anonymize_dataset.py
"""Tests for the anonymization tool with 100% synthetic fixtures (never real data)."""
import csv
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "tools" / "anonymize_dataset.py"


def make_real_fixtures(d: Path) -> None:
    """FICTIONAL source data with the same shape as the real files."""
    (d / "articulos_proveedor.csv").write_text(
        "Columna1,IdArticulo,Articulo,FechaUltimaCompra,UltimoProveedor\n"
        "0,AB111,VALVULA BOLA 1/2 LATON,2025-03-18,Proveedor Ficticio SA\n"
        "1,AB222,CODO INOX DN50,,Proveedor Ficticio SA\n"
        "2,,fila sin id,,\n"
        "3,AB111,duplicado de AB111,,\n"
        "4,AB333,CONTACTO: Empresa Ficticia - 680559813 norma DIN 10242,,\n",
        encoding="utf-8")
    (d / "historico_pedidos_rows.csv").write_text(
        "id,user_text,catalog_description,order_number,frequency,last_used,confidence_score,"
        "created_at,user_id,id_articulo_catalogo\n"
        "1,valvula de Empresa Ficticia pedido 10417,VALVULA BOLA 1/2 LATON,10417,2,"
        "2025-03-18 05:30:37+00,1,2025-03-28,u1,AB111\n"
        "2,codo cincuenta,CODO INOX DN50,11222,1,2025-04-02,1,2025-04-02,u2,AB222\n"
        "3,huerfano,X,11223,1,2025-04-02,1,2025-04-02,u3,ZZ999\n"
        "4,sin id,X,11224,1,2025-04-02,1,2025-04-02,u4,\n",
        encoding="utf-8")
    pair = {"messages": [
        {"role": "system", "content": "s"},
        {"role": "user", "content": "Pedido Empresa Ficticia 10 417, 2 valvulas de bola"},
        {"role": "assistant", "content": "DESCRIPCION,CANTIDAD\r\nVALVULA BOLA 1/2 LATON,2.0\r\n"},
    ]}
    (d / "fine-tuning").mkdir()
    (d / "fine-tuning" / "fine_tuning.jsonl").write_text(json.dumps(pair) + "\n", encoding="utf-8")


def run_tool(tmp_path: Path) -> tuple[subprocess.CompletedProcess, Path]:
    real = tmp_path / "real"
    real.mkdir()
    make_real_fixtures(real)
    repl = tmp_path / "repl.txt"
    repl.write_text("Empresa Ficticia=>[customer]\n", encoding="utf-8")
    out = tmp_path / "data"
    env = {"REAL_DATA_DIR": str(real), "ANON_SALT": "salt-de-test",
           "REAL_REPLACEMENTS_FILE": str(repl),
           "SYSTEMROOT": "C:\\Windows", "PATH": "C:\\Windows\\System32"}
    proc = subprocess.run([sys.executable, str(TOOL), "--output", str(out)],
                          capture_output=True, text=True, cwd=str(tmp_path), env=env)
    return proc, out


def test_tool_generates_complete_anonymized_dataset(tmp_path):
    proc, out = run_tool(tmp_path)
    assert proc.returncode == 0, proc.stderr + proc.stdout

    # catalog: 3 valid rows (no-id and duplicate dropped), tokenized ids
    rows = list(csv.DictReader(open(out / "catalog.csv", encoding="utf-8")))
    assert len(rows) == 3
    assert all(r["id_articulo"].startswith("ART-") for r in rows)
    cat_text = (out / "catalog.csv").read_text(encoding="utf-8")
    assert "AB111" not in cat_text
    assert rows[0]["ultima_compra_mes"] == "2025-03"
    # admin row: term + phone sanitized, DIN norm number untouched (no [order-ref] in catalog)
    admin = rows[2]["articulo"]
    assert "[customer]" in admin and "[phone]" in admin
    assert "680559813" not in cat_text
    assert "DIN 10242" in admin

    # historical: 2 rows (orphan and no-id dropped), sanitized text, consistent FK
    hrows = list(csv.DictReader(open(out / "historical.csv", encoding="utf-8")))
    assert len(hrows) == 2
    cat_ids = {r["id_articulo"] for r in rows}
    assert all(h["id_articulo"] in cat_ids for h in hrows)
    assert "[customer]" in hrows[0]["user_text"]
    assert "[order-ref]" in hrows[0]["user_text"]
    assert "10417" not in hrows[0]["user_text"]
    # forbidden columns are gone
    assert "order_number" not in hrows[0] and "user_id" not in hrows[0]

    # pairs: sanitized
    pair = json.loads((out / "extraction_pairs.jsonl").read_text(encoding="utf-8"))
    assert "[customer]" in pair["transcription"] and "[order-ref]" in pair["transcription"]
    assert pair["expected_items"][0]["description"] == "VALVULA BOLA 1/2 LATON"

    # README with counters + manual review report
    readme = (out / "README.md").read_text(encoding="utf-8")
    assert "| 2 |" in readme
    assert (tmp_path / ".tmp" / "manual_review.txt").is_file()


def test_same_real_id_same_token_across_files(tmp_path):
    proc, out = run_tool(tmp_path)
    assert proc.returncode == 0
    cat = {r["articulo"]: r["id_articulo"]
           for r in csv.DictReader(open(out / "catalog.csv", encoding="utf-8"))}
    hist = list(csv.DictReader(open(out / "historical.csv", encoding="utf-8")))
    # the valve row in historical points at the SAME token as the catalog
    assert hist[0]["id_articulo"] == cat["VALVULA BOLA 1/2 LATON"]


def test_tool_fails_without_env(tmp_path):
    proc = subprocess.run([sys.executable, str(TOOL)], capture_output=True, text=True,
                          cwd=str(tmp_path),
                          env={"SYSTEMROOT": "C:\\Windows", "PATH": "C:\\Windows\\System32"})
    assert proc.returncode != 0
    assert "REAL_DATA_DIR" in proc.stdout + proc.stderr
