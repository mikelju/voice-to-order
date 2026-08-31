# tests/tools/test_history_sweep.py
"""Tests for the full-history real-terms sweep, on throwaway git repos."""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "tools" / "history_sweep.py"

TERM = "Acmecorp"          # stand-in for a real term; never a real one in tests
CLEAN_TEXT = "id_articulo,articulo\nART-0123456789,VALVULA BOLA 1/2 LATON\n"


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   capture_output=True, text=True)


def make_repo(tmp_path: Path, content: str, message: str = "initial") -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "test")
    (repo / "data.csv").write_text(content, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)
    return repo


def run(repo: Path, terms_file: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(TOOL), "--terms", str(terms_file),
                           "--repo", str(repo)], capture_output=True, text=True)


def terms_file(tmp_path: Path) -> Path:
    p = tmp_path / "terms.txt"
    p.write_text(f"{TERM}\n", encoding="utf-8")
    return p


def test_clean_history_passes(tmp_path):
    repo = make_repo(tmp_path, CLEAN_TEXT)
    proc = run(repo, terms_file(tmp_path))
    assert proc.returncode == 0, proc.stdout
    assert "CLEAN" in proc.stdout


def test_term_in_a_blob_fails(tmp_path):
    repo = make_repo(tmp_path, f"{CLEAN_TEXT}ART-abcdef0123,TUBO {TERM} DN20\n")
    proc = run(repo, terms_file(tmp_path))
    assert proc.returncode == 1, proc.stdout
    assert "data.csv" in proc.stdout


def test_term_deleted_from_head_still_fails(tmp_path):
    """The whole point: a term removed in a later commit still lives in history."""
    repo = make_repo(tmp_path, f"{CLEAN_TEXT}ART-abcdef0123,TUBO {TERM} DN20\n")
    (repo / "data.csv").write_text(CLEAN_TEXT, encoding="utf-8")
    git(repo, "commit", "-aqm", "sanitize the working tree")
    proc = run(repo, terms_file(tmp_path))
    assert proc.returncode == 1, proc.stdout
    assert "blob" in proc.stdout


def test_term_in_a_commit_message_fails(tmp_path):
    repo = make_repo(tmp_path, CLEAN_TEXT, message=f"remove the {TERM} rows")
    proc = run(repo, terms_file(tmp_path))
    assert proc.returncode == 1, proc.stdout
    assert "message" in proc.stdout


def test_output_never_prints_the_term(tmp_path):
    """The report must be safe to paste anywhere - that is how fix-2 happened."""
    repo = make_repo(tmp_path, f"{CLEAN_TEXT}ART-abcdef0123,TUBO {TERM} DN20\n",
                     message=f"add {TERM}")
    proc = run(repo, terms_file(tmp_path))
    assert TERM.lower() not in (proc.stdout + proc.stderr).lower()


def test_case_variants_are_matched(tmp_path):
    repo = make_repo(tmp_path, f"{CLEAN_TEXT}ART-abcdef0123,TUBO {TERM.upper()} DN20\n")
    proc = run(repo, terms_file(tmp_path))
    assert proc.returncode == 1, proc.stdout
