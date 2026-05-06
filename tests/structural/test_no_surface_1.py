"""Structural fence: prevent Surface 1 from being re-introduced (HUG-193).

Surface 1 was the original `POST /ask` + `nl_engine.engine` path that
generated SQL via a keyword router + prose grounding YAMLs. It was
retired once the LangGraph agent on Surface 2 cleared the must-pass
gate (≥ 80%, HUG-190 ledger row 0cdf3fa).

This test asserts the deletion is durable — re-introducing any of the
files / imports / route / frontend client below requires a new ADR
amendment and a Linear ticket.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGES = REPO_ROOT / "packages"
NL_ENGINE_SRC = PACKAGES / "nl-engine" / "src"
API_SRC = PACKAGES / "api" / "src"
FRONTEND_SRC = PACKAGES / "frontend" / "src"

_DELETED_FILES = (
    "packages/api/src/api/routes/ask.py",
    "packages/nl-engine/src/nl_engine/engine.py",
    "packages/nl-engine/src/nl_engine/context_selector.py",
    "packages/nl-engine/src/nl_engine/sql_validator.py",
    "packages/nl-engine/src/nl_engine/context_loader.py",
    "packages/nl-engine/context/schema_context.yaml",
    "packages/nl-engine/context/metrics.yaml",
    "packages/nl-engine/context/examples.yaml",
    "packages/nl-engine/context/rules.yaml",
)

_FORBIDDEN_IMPORTS = (
    "nl_engine.engine",
    "nl_engine.context_selector",
    "nl_engine.sql_validator",
    "nl_engine.context_loader",
)

_REASON = (
    "Surface 1 was retired in HUG-193. Re-introducing it requires a new "
    "ADR amendment + Linear ticket. The successor surface is the LangGraph "
    "agent at /threads."
)


def test_surface_1_files_do_not_exist() -> None:
    existing = [p for p in _DELETED_FILES if (REPO_ROOT / p).exists()]
    assert not existing, f"{_REASON}\nThese files came back: {existing}"


def _iter_python_sources() -> list[Path]:
    """All non-test, non-tooling Python files we'd consider production
    code. Tests are excluded so the fence doesn't trip on a test-suite
    artifact (an ignored example of a forbidden import)."""
    out: list[Path] = []
    for root in (NL_ENGINE_SRC, API_SRC):
        out.extend(p for p in root.rglob("*.py") if p.is_file())
    return out


def test_no_python_source_imports_surface_1() -> None:
    bad: list[str] = []
    pattern = re.compile(
        r"(?:from|import)\s+("
        + "|".join(re.escape(m) for m in _FORBIDDEN_IMPORTS)
        + r")\b"
    )
    for path in _iter_python_sources():
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if pattern.search(stripped):
                bad.append(f"{path.relative_to(REPO_ROOT)}: {stripped}")
    assert not bad, f"{_REASON}\nForbidden imports:\n  - " + "\n  - ".join(bad)


def test_main_py_does_not_register_ask_router() -> None:
    main_py = (API_SRC / "api" / "main.py").read_text(encoding="utf-8")
    assert "from api.routes import" in main_py, (
        "main.py routing block missing — test fence is stale, not a real failure"
    )
    assert "ask" not in re.findall(
        r"from api\.routes import \(([^)]+)\)", main_py, re.DOTALL
    )[0].split(","), f"{_REASON}\n`ask` router is back in main.py."
    assert "include_router(ask" not in main_py, (
        f"{_REASON}\n`include_router(ask...)` re-added to main.py."
    )


def test_no_postask_in_frontend() -> None:
    if not FRONTEND_SRC.exists():
        return
    bad: list[str] = []
    for path in FRONTEND_SRC.rglob("*"):
        if not path.is_file() or path.suffix not in {".ts", ".tsx", ".js", ".jsx"}:
            continue
        text = path.read_text(encoding="utf-8")
        if "postAsk" in text:
            bad.append(str(path.relative_to(REPO_ROOT)))
    assert not bad, (
        f"{_REASON}\nFrontend file(s) reference postAsk:\n  - "
        + "\n  - ".join(bad)
    )
