# tests/tools/test_generate_embeddings.py
"""Phase-4 generator: batching+retry with a fake client, and source loading. No network."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

import generate_embeddings as gen  # noqa: E402
from emblib import DIM  # noqa: E402


class FakeClient:
    def __init__(self, fail_first=0):
        self.calls = 0
        self.fail_first = fail_first
        self.batch_sizes = []

        outer = self

        class Embeddings:
            def create(self, model, input, dimensions):
                outer.calls += 1
                if outer.calls <= outer.fail_first:
                    raise RuntimeError("rate limit")
                outer.batch_sizes.append(len(input))
                assert dimensions == DIM
                return SimpleNamespace(
                    data=[SimpleNamespace(embedding=[0.5] * DIM) for _ in input])
        self.embeddings = Embeddings()


def test_embed_batched_splits_batches(monkeypatch):
    client = FakeClient()
    out = gen.embed_batched(client, [f"t{i}" for i in range(2300)])
    assert len(out) == 2300
    assert client.batch_sizes == [1000, 1000, 300]


def test_embed_batched_retries(monkeypatch):
    monkeypatch.setattr(gen.time, "sleep", lambda s: None)
    client = FakeClient(fail_first=2)
    out = gen.embed_batched(client, ["a", "b"])
    assert len(out) == 2
    assert client.calls == 3   # 2 failures + 1 success


def test_embed_batched_gives_up(monkeypatch):
    monkeypatch.setattr(gen.time, "sleep", lambda s: None)
    client = FakeClient(fail_first=99)
    with pytest.raises(RuntimeError):
        gen.embed_batched(client, ["a"])


def test_load_sources(tmp_path):
    (tmp_path / "catalog.csv").write_text(
        "id_articulo,articulo,ultima_compra_mes\n"
        "ART-0000000001,TACO 10,2025-01\n"
        "ART-0000000002,,\n"                       # empty description -> skipped
        "ART-0000000003,\"TUBO\nMULTILINEA\",\n",  # newline flattened
        encoding="utf-8")
    (tmp_path / "historical.csv").write_text(
        "user_text,catalog_description,id_articulo,frequency,last_used_month\n"
        "taco de 10,TACO 10,ART-0000000001,2,2025-01\n"
        "taco de 10,OTRA DESC,ART-0000000001,1,2025-02\n",   # dup text -> dedup
        encoding="utf-8")
    (tmp_path / "extraction_pairs.jsonl").write_text(
        json.dumps({"transcription": "t", "expected_items": [
            {"qty": "1.0", "description": "TACO 10"},
            {"qty": "2.0", "description": "TACO 10"},      # dup -> dedup
            {"qty": "1.0", "description": "TUERCA M10"}]}) + "\n",
        encoding="utf-8")
    src = gen.load_sources(tmp_path)
    cat_keys, cat_texts = src["catalog"]
    assert cat_keys == ["ART-0000000001", "ART-0000000003"]
    assert cat_texts[1] == "TUBO MULTILINEA"
    assert src["historical"][0] == ["taco de 10"]
    assert src["queries"][0] == ["TACO 10", "TUERCA M10"]
