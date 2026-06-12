# tests/tools/test_emblib.py
"""Phase-4 file format: stdlib round-trip, no network. Spec: versioned format."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from emblib import DIM, read_embeddings, write_embeddings  # noqa: E402


def test_round_trip(tmp_path):
    ids = ["ART-0123456789", "una descripción con tildes Ø", "TACO 10"]
    vectors = [[float(i) / 7 + j for j in range(DIM)] for i in range(3)]
    write_embeddings(tmp_path / "demo", ids, vectors)
    out_ids, out_vecs = read_embeddings(tmp_path / "demo")
    assert out_ids == ids
    for a, b in zip(vectors, out_vecs):
        assert b == pytest.approx(a, rel=1e-6)   # float32 precision


def test_length_mismatch_rejected(tmp_path):
    with pytest.raises(ValueError):
        write_embeddings(tmp_path / "x", ["a"], [])


def test_wrong_dim_rejected(tmp_path):
    with pytest.raises(ValueError):
        write_embeddings(tmp_path / "x", ["a"], [[0.0] * (DIM - 1)])


def test_corrupt_file_detected(tmp_path):
    write_embeddings(tmp_path / "x", ["a"], [[0.0] * DIM])
    f32 = tmp_path / "x.f32"
    f32.write_bytes(f32.read_bytes()[:-4])
    with pytest.raises(ValueError):
        read_embeddings(tmp_path / "x")
