"""HUG-181: each DSPy module instantiates cleanly + the loader returns
None when the compiled artifact is missing (fallback path)."""

from __future__ import annotations

import json
from pathlib import Path

import dspy
import pytest
from nl_engine.agent import prompts as prompts_pkg
from nl_engine.agent.prompts import (
    Clarify,
    MetricFlowQueryWriter,
    PlanQuestion,
    RenderChartSpec,
    Summarize,
    load_compiled,
)


@pytest.mark.parametrize(
    "cls",
    [PlanQuestion, MetricFlowQueryWriter, RenderChartSpec, Summarize, Clarify],
)
def test_module_constructs_without_lm(cls: type[dspy.Module]) -> None:
    """The hand-written signature must be valid Python — instantiating
    a module shouldn't require an LM (only `forward()` does)."""
    instance = cls()
    assert isinstance(instance, dspy.Module)


def test_all_modules_listed() -> None:
    """Sanity: the module list in __init__ matches the five files."""
    assert len(prompts_pkg.ALL_MODULES) == 5


def test_load_compiled_returns_none_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When `compiled/<name>.json` is absent, load_compiled returns
    None so the agent falls back to the hand-written signature."""
    monkeypatch.setattr(
        "nl_engine.agent.prompts.loader.COMPILED_DIR", tmp_path
    )
    assert load_compiled("does_not_exist") is None


def test_load_compiled_returns_none_on_bad_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Garbage on disk → loader logs + returns None (never raises)."""
    bad = tmp_path / "broken.json"
    bad.write_text(json.dumps({"this": "is not a dspy artifact"}))
    monkeypatch.setattr(
        "nl_engine.agent.prompts.loader.COMPILED_DIR", tmp_path
    )
    assert load_compiled("broken") is None
