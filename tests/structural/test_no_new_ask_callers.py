"""Soft fence preventing new callers of Surface 1 (/ask, engine.ask) during the
deprecation runway. Superseded by `tests/structural/test_no_surface_1.py` once
HUG-193 deletes Surface 1 entirely.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Phase B (frontend half) flips on inside the final commit of HUG-179.
_FRONTEND_FENCE_ACTIVE = False

_BACKEND_SCAN_ROOTS = [
    REPO_ROOT / "packages" / "api" / "src",
    REPO_ROOT / "packages" / "nl-engine" / "src",
]
_BACKEND_ALLOWLIST = {
    REPO_ROOT / "packages" / "api" / "src" / "api" / "routes" / "ask.py",
    REPO_ROOT / "packages" / "api" / "src" / "api" / "routes" / "history.py",
    REPO_ROOT / "packages" / "api" / "src" / "api" / "repo" / "history.py",
    # Type-only imports of AnswerResponse / ClarificationResponse for the
    # eval grader (HUG-188). The grader will outlive Surface 1; HUG-193
    # will move these typed shapes out of engine.py before deletion.
    REPO_ROOT / "packages" / "nl-engine" / "src" / "nl_engine" / "benchmarks"
    / "grader" / "categorize.py",
    REPO_ROOT / "packages" / "nl-engine" / "src" / "nl_engine" / "benchmarks"
    / "grader" / "grade.py",
}
_BACKEND_GLOB_ALLOWLIST = (
    "**/tests/**",
    "**/benchmarks/**",
)
_BACKEND_PATTERNS = [
    re.compile(r"\bfrom\s+nl_engine\.engine\s+import\b"),
    re.compile(r"\bimport\s+nl_engine\.engine\b"),
    re.compile(r"\bnl_engine\.engine\."),
    re.compile(r"\bengine_ask\b"),
]

_FRONTEND_SCAN_ROOT = REPO_ROOT / "packages" / "frontend" / "src"
_FRONTEND_GLOB_EXCLUDES = (
    "**/__tests__/**",
    "**/*.test.ts",
    "**/*.test.tsx",
    "**/*.stories.ts",
    "**/*.stories.tsx",
)
_FRONTEND_PATTERNS = [
    re.compile(r"/api/ask\b"),
    re.compile(r"\bpostAsk\b"),
]

_RESOLUTION_HINT = (
    "Surface 1 (engine.ask / /ask) is on a deprecation runway — see HUG-193. "
    "New callers are blocked. If this is intentional and motivated by data, "
    "comment on HUG-193 and amend the allowlist; otherwise route the call "
    "through the agent (/threads)."
)


def _is_allowlisted(
    path: Path, exact: set[Path], globs: tuple[str, ...]
) -> bool:
    if path in exact:
        return True
    return any(path.match(g) for g in globs)


def _scan(
    roots: list[Path],
    exact_allow: set[Path],
    glob_allow: tuple[str, ...],
    patterns: list[re.Pattern[str]],
    suffix: str,
) -> list[str]:
    violations: list[str] = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob(f"*{suffix}"):
            if _is_allowlisted(p, exact_allow, glob_allow):
                continue
            try:
                text = p.read_text()
            except (OSError, UnicodeDecodeError):
                continue
            for line_no, line in enumerate(text.splitlines(), start=1):
                for pat in patterns:
                    if pat.search(line):
                        rel = p.relative_to(REPO_ROOT)
                        violations.append(f"{rel}:{line_no}: {line.strip()}")
                        break
    return violations


def test_no_new_backend_callers_of_surface_1() -> None:
    violations = _scan(
        _BACKEND_SCAN_ROOTS,
        _BACKEND_ALLOWLIST,
        _BACKEND_GLOB_ALLOWLIST,
        _BACKEND_PATTERNS,
        ".py",
    )
    assert not violations, (
        f"\n\n{_RESOLUTION_HINT}\n\nNew callers found:\n  "
        + "\n  ".join(violations)
    )


def test_no_new_frontend_callers_of_surface_1() -> None:
    if not _FRONTEND_FENCE_ACTIVE:
        return
    violations: list[str] = []
    if _FRONTEND_SCAN_ROOT.exists():
        for suffix in (".ts", ".tsx"):
            for p in _FRONTEND_SCAN_ROOT.rglob(f"*{suffix}"):
                if _is_allowlisted(p, set(), _FRONTEND_GLOB_EXCLUDES):
                    continue
                try:
                    text = p.read_text()
                except (OSError, UnicodeDecodeError):
                    continue
                for line_no, line in enumerate(text.splitlines(), start=1):
                    for pat in _FRONTEND_PATTERNS:
                        if pat.search(line):
                            rel = p.relative_to(REPO_ROOT)
                            violations.append(
                                f"{rel}:{line_no}: {line.strip()}"
                            )
                            break
    assert not violations, (
        f"\n\n{_RESOLUTION_HINT}\n\nNew callers found:\n  "
        + "\n  ".join(violations)
    )
