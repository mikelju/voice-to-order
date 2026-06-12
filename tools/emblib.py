# tools/emblib.py
"""Versioned embedding files, stdlib only.

Format per dataset (`<base>.ids.txt` + `<base>.f32`):
- `<base>.ids.txt`: one key per line (UTF-8). Line i belongs to vector i.
- `<base>.f32`: N x DIM float32, little-endian, concatenated.

DIM is fixed at 256 (the Phase-2 schema contract, reduced-dimension
text-embedding-3-small).
"""
from __future__ import annotations

import sys
from array import array
from pathlib import Path

DIM = 256


def write_embeddings(base: str | Path, ids: list[str], vectors: list[list[float]]) -> None:
    if len(ids) != len(vectors):
        raise ValueError(f"ids ({len(ids)}) and vectors ({len(vectors)}) differ")
    base = Path(base)
    base.parent.mkdir(parents=True, exist_ok=True)
    flat = array("f")
    for vec in vectors:
        if len(vec) != DIM:
            raise ValueError(f"vector of dim {len(vec)}, expected {DIM}")
        flat.extend(vec)
    if sys.byteorder == "big":
        flat.byteswap()
    with open(f"{base}.ids.txt", "w", encoding="utf-8", newline="\n") as f:
        for key in ids:
            if "\n" in key or "\r" in key:
                raise ValueError(f"key contains a newline: {key[:40]!r}")
            f.write(key + "\n")
    with open(f"{base}.f32", "wb") as f:
        flat.tofile(f)


def read_embeddings(base: str | Path) -> tuple[list[str], list[list[float]]]:
    base = Path(base)
    ids = Path(f"{base}.ids.txt").read_text(encoding="utf-8").splitlines()
    flat = array("f")
    raw = Path(f"{base}.f32").read_bytes()
    flat.frombytes(raw)
    if sys.byteorder == "big":
        flat.byteswap()
    if len(flat) != len(ids) * DIM:
        raise ValueError(f"{base}.f32 holds {len(flat)} floats, "
                         f"expected {len(ids)} x {DIM}")
    vectors = [list(flat[i * DIM:(i + 1) * DIM]) for i in range(len(ids))]
    return ids, vectors
