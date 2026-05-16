"""CI-workflow → eval-script CLI drift gate (HUG-236).

Every flag passed to `scripts/eval.py` in any `.github/workflows/*.yml`
must be recognised by `run_eval._build_parser()`. Catches the exact
class of bug observed on 2026-05-16: `nl-eval.yml` invoked
`uv run python scripts/eval.py --full` after HUG-193 removed `--full`,
crashing every NL Eval run at argparse before the benchmark could
even start.

Discovery walks the YAML files as text (no PyYAML dep) — robust to
multi-line `run:` blocks, line-continuations (`\\`), and either quote
style.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
BENCHMARKS = REPO_ROOT / "packages" / "nl-engine" / "benchmarks"


def _known_flags() -> set[str]:
    """The set of CLI flags `_build_parser()` recognises."""
    sys.path.insert(0, str(BENCHMARKS))
    try:
        import run_eval  # type: ignore[import-not-found]
    finally:
        sys.path.pop(0)
    parser = run_eval._build_parser()
    flags: set[str] = set()
    for action in parser._actions:
        for opt in action.option_strings:
            flags.add(opt)
    return flags


_EVAL_INVOCATION_NEEDLE = "scripts/eval.py"
_FLAG_RE = re.compile(r"(?:^|\s)(--[a-z][a-z0-9-]*)")


def _flags_used_in(yml_text: str) -> list[tuple[int, str]]:
    """Return (1-indexed-line-no, flag) tuples for every `--flag` after
    a `scripts/eval.py` invocation in `yml_text`.

    Walks line-by-line. When a line contains `scripts/eval.py`, the
    *logical* command is the join of that line plus every subsequent
    line until one doesn't end with `\\`. All flags in the logical
    command are attributed to the start line.
    """
    found: list[tuple[int, str]] = []
    lines = yml_text.splitlines()
    i = 0
    while i < len(lines):
        if _EVAL_INVOCATION_NEEDLE in lines[i]:
            start_line = i + 1  # 1-indexed
            chunk = [lines[i]]
            # Follow shell-line continuations.
            while chunk[-1].rstrip().endswith("\\") and i + 1 < len(lines):
                i += 1
                chunk.append(lines[i])
            logical = " ".join(c.rstrip().rstrip("\\") for c in chunk)
            for flag in _FLAG_RE.findall(logical):
                found.append((start_line, flag))
        i += 1
    return found


@pytest.mark.parametrize("yml_path", sorted(WORKFLOWS.glob("*.yml")))
def test_workflow_eval_flags_recognised(yml_path: Path) -> None:
    """For each workflow, every flag handed to scripts/eval.py must be
    in run_eval._build_parser()'s known-flags set."""
    text = yml_path.read_text()
    used = _flags_used_in(text)
    if not used:
        pytest.skip(f"{yml_path.name} has no scripts/eval.py invocations")
    known = _known_flags()
    unknown = [
        (yml_path.name, line, flag)
        for line, flag in used
        if flag not in known
    ]
    assert not unknown, (
        f"Stale CLI flag(s) in {yml_path.name} not recognised by "
        f"run_eval._build_parser(): {unknown}. Known flags: "
        f"{sorted(known)}."
    )
