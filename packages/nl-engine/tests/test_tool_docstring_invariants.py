"""Pin the prompt-bearing strings in `agent.tools` against silent
regression.

Every docstring and `Field(description=...)` listed here is serialized
by LangChain into the tool schema the LLM sees. Trimming them changes
agent behavior at runtime — the HUG-200 telemetry commit accidentally
trimmed several of these and dropped must-pass eval accuracy from 83%
to 42% (see ADR-0006).

If you intentionally want to change one of these strings: update this
test AND re-run `make eval` before merging.
"""

from __future__ import annotations

import pytest
from nl_engine.agent.tools import (
    MfQueryArgs,
    final_answer,
    list_metrics,
    lookup_metric_definition,
    mf_query,
)

_TRIM_WARNING = (
    "This docstring is a production prompt, not just documentation. "
    "The LLM reads it as instructions. If you intentionally want to "
    "change it, update this test AND re-run `make eval` before merging."
)


def _doc(t: object) -> str:
    """Pull the docstring LangChain serializes for a @tool function."""
    fn = getattr(t, "func", t)
    return (getattr(fn, "__doc__", None) or "")


def _field_desc(model_cls: type, field_name: str) -> str:
    return model_cls.model_fields[field_name].description or ""


@pytest.mark.parametrize(
    ("phrase", "where"),
    [
        # mf_query.__doc__ — verbatim copy + worked dimension example +
        # ASC/DESC syntax warning + did-you-mean recovery rule.
        ("VERBATIM", _doc(mf_query)),
        ("deposits_monthly_grain__branch", _doc(mf_query)),
        ("metric_time__month", _doc(mf_query)),
        ("ASC", _doc(mf_query)),
        ("DESC", _doc(mf_query)),
        ("did you mean", _doc(mf_query)),
        # MfQueryArgs.dimensions — verbatim copy + concrete examples +
        # explicit "do not paraphrase" guard.
        ("verbatim", _field_desc(MfQueryArgs, "dimensions")),
        ("NEVER paraphrase", _field_desc(MfQueryArgs, "dimensions")),
        ("metric_time__month", _field_desc(MfQueryArgs, "dimensions")),
        # MfQueryArgs.where — Jinja Dimension() format guidance.
        ("Dimension(", _field_desc(MfQueryArgs, "where")),
        ("{{", _field_desc(MfQueryArgs, "where")),
        # Time-range upper-bound-exclusive guidance (Q12 fix: agent used
        # `<= '2026-03-01'` and missed March because MF compares against
        # underlying timestamps even for month-grain dims).
        ("EXCLUSIVE upper bound", _field_desc(MfQueryArgs, "where")),
        ("< '2026-04-01'", _field_desc(MfQueryArgs, "where")),
        # MfQueryArgs.order — bare-name + `-` syntax + ASC/DESC ban.
        ("ASC", _field_desc(MfQueryArgs, "order")),
        ("DESC", _field_desc(MfQueryArgs, "order")),
        ("rejects them outright", _field_desc(MfQueryArgs, "order")),
        # list_metrics.__doc__ — explicit "FIRST" guidance + "do not
        # paraphrase" guard + literal example.
        ("FIRST", _doc(list_metrics)),
        ("Do NOT paraphrase", _doc(list_metrics)),
        ("deposits_monthly_grain__branch", _doc(list_metrics)),
        # lookup_metric_definition.__doc__ — when-to-use guidance.
        ("list_metrics()", _doc(lookup_metric_definition)),
        # final_answer.__doc__ — when-to-populate-DSL + when-to-leave-empty.
        ("openui_dsl", _doc(final_answer)),
        ("system prompt", _doc(final_answer)),
        ("None", _doc(final_answer)),
        # final_answer.__doc__ — self-consistency guard (rows/mf_query/summary
        # must describe the same answer; addresses the Q13 carryover failure
        # mode where the agent's probe-query rows leak into the final answer
        # after a refined query).
        ("self-consistent", _doc(final_answer)),
        ("exactly that single matching", _doc(final_answer)),
        ("Never carry rows from an earlier", _doc(final_answer)),
        # No-post-processing rule (Q15 fix: agent renamed
        # `past_due_loan_count` → `30_plus_past_due_loan_count` and
        # client-side-aggregated 4 bucket rows into 1, breaking the
        # grader's column-name match).
        ("LITERAL rows MetricFlow returned", _doc(final_answer)),
        ("do not aggregate the rows client-side", _doc(final_answer)),
    ],
)
def test_prompt_bearing_string_contains_phrase(phrase: str, where: str) -> None:
    assert phrase in where, (
        f"missing phrase {phrase!r} from a prompt-bearing string. "
        f"{_TRIM_WARNING}"
    )


def test_mf_query_docstring_has_minimum_length() -> None:
    """The mf_query docstring carries the agent's hot-path instructions.
    Going much under ~700 chars almost certainly means a worked example
    or warning has been dropped."""
    doc = _doc(mf_query)
    assert len(doc) >= 700, (
        f"mf_query docstring shrank to {len(doc)} chars. {_TRIM_WARNING}"
    )


def test_dimensions_field_description_has_minimum_length() -> None:
    """Same logic for the dimensions Field description — the most
    failure-prone arg."""
    desc = _field_desc(MfQueryArgs, "dimensions")
    assert len(desc) >= 300, (
        f"MfQueryArgs.dimensions description shrank to {len(desc)} chars. "
        f"{_TRIM_WARNING}"
    )
