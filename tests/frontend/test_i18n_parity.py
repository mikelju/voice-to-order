# tests/frontend/test_i18n_parity.py
"""Static checks over the frontend i18n dictionary (deviation 5.1).

The frontend has no test framework (accepted debt, phase 5), and the ES/EN dictionary
was kept in parity by hand. These checks parse `i18n.tsx` as text so the guarantee is
automated without adding a JS toolchain:

- both dictionaries expose exactly the same keys,
- no empty translations,
- every `t('...')` literal used by a component exists in the dictionary.
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
I18N = REPO / "src" / "frontend" / "src" / "i18n.tsx"
SRC = REPO / "src" / "frontend" / "src"

KEY_RE = re.compile(r"^\s*'([^']+)':\s*(.*?),?\s*$", re.M)
USED_RE = re.compile(r"\bt\(\s*'([^']+)'")


def dictionary(name: str) -> dict[str, str]:
    body = I18N.read_text(encoding="utf-8")
    block = re.search(rf"const {name}: Dict = \{{(.*?)\n\}};", body, re.S)
    assert block, f"dictionary {name} not found in i18n.tsx"
    return {m.group(1): m.group(2) for m in KEY_RE.finditer(block.group(1))}


def test_both_dictionaries_are_non_trivial():
    assert len(dictionary("ES")) > 50
    assert len(dictionary("EN")) > 50


def test_key_sets_are_identical():
    es, en = dictionary("ES"), dictionary("EN")
    assert set(es) == set(en), (
        f"only in ES: {sorted(set(es) - set(en))} | only in EN: {sorted(set(en) - set(es))}")


def test_no_empty_translations():
    for name in ("ES", "EN"):
        empty = [k for k, v in dictionary(name).items() if v.strip(" ',\"") == ""]
        assert not empty, f"{name} has empty values: {empty}"


def test_every_used_key_exists():
    keys = set(dictionary("ES"))
    missing: dict[str, list[str]] = {}
    for path in SRC.rglob("*.tsx"):
        if path.name == "i18n.tsx":
            continue
        used = set(USED_RE.findall(path.read_text(encoding="utf-8")))
        absent = sorted(used - keys)
        if absent:
            missing[path.name] = absent
    assert not missing, f"t() calls with no dictionary entry: {missing}"


def test_interpolation_placeholders_match_across_languages():
    es, en = dictionary("ES"), dictionary("EN")
    ph = lambda s: set(re.findall(r"\{(\w+)\}", s))
    mismatched = {k: (ph(es[k]), ph(en[k])) for k in es if ph(es[k]) != ph(en.get(k, ""))}
    assert not mismatched, f"placeholder mismatch: {mismatched}"
