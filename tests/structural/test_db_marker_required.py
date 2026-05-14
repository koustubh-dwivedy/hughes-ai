"""Any test file that actually connects to Postgres must carry the
`@pytest.mark.db` marker (HUG-229).

The marker routes the file into CI's `integration-test` job
(`pytest -m db`) and out of the `unit-test` job (`pytest -m "not db"`).
Forgetting the marker means the test either runs in the wrong job
(failing the no-DB unit-test stage) or silently skips inside the
file's own `pytest.skip("DATABASE_URL not set")` fallback — the
exact harness-engineering anti-pattern this gate exists to catch.

Detection rule: a file is DB-backed if it contains a real
`psycopg.connect(` call (not just the string inside a `patch(...)`
expression — `test_executor.py` mocks `psycopg.connect` and is NOT
a real DB user). Then assert the file declares
`pytestmark = pytest.mark.db` near the top.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_TEST_GLOBS = [
    _REPO / "packages" / "api" / "tests",
    _REPO / "packages" / "nl-engine" / "tests",
    _REPO / "tests" / "integration",
]

_REAL_CONNECT = re.compile(r"^[^#\"'\n]*psycopg\.connect\(", re.MULTILINE)
_MARK_DECL = re.compile(
    r"^pytestmark\s*=\s*pytest\.mark\.db\b",
    re.MULTILINE,
)


def _collect_test_files() -> list[Path]:
    out: list[Path] = []
    for d in _TEST_GLOBS:
        if not d.exists():
            continue
        out.extend(sorted(d.rglob("test_*.py")))
    return out


def _is_real_db_test(text: str) -> bool:
    # A line containing `psycopg.connect(` but ALSO containing `patch(`
    # or a string-literal context indicates a mock. Filter those out.
    for line in text.splitlines():
        if "psycopg.connect(" not in line:
            continue
        if "patch(" in line or 'patch."' in line:
            continue
        stripped = line.lstrip()
        # Heuristic: if it's not inside a quoted string in the source
        # (typical mock case: `patch("nl_engine.executor.psycopg.connect", ...)`),
        # treat as real.
        if not (stripped.startswith('"') or stripped.startswith("'")):
            return True
    return False


@pytest.mark.parametrize("path", _collect_test_files())
def test_db_files_declare_marker(path: Path) -> None:
    body = path.read_text()
    if not _is_real_db_test(body):
        return  # not a DB test; skip silently
    assert _MARK_DECL.search(body), (
        f"{path.relative_to(_REPO)} calls psycopg.connect() but is missing\n"
        f"  pytestmark = pytest.mark.db\n"
        "near the top of the file. Without it, the test either runs in the\n"
        "wrong CI job or silently skips when DATABASE_URL is unset. Add the\n"
        "line right after the imports."
    )
