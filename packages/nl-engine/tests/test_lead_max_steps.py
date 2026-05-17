"""Constant locks for the per-path step caps.

`LEAD_MAX_STEPS_PER_TURN` is intentionally higher than
`MAX_STEPS_PER_TURN` because the lead agent pays one LLM call per
propose_plan / run_subagent / write_memory / final_answer; a typical
deep question needs ~6-12 calls plus replan headroom. Bumping either
constant should require a deliberate test edit, not slip through review.
"""

from __future__ import annotations

from nl_engine.agent.state import LEAD_MAX_STEPS_PER_TURN, MAX_STEPS_PER_TURN


def test_chat_max_steps_per_turn_is_ten() -> None:
    assert MAX_STEPS_PER_TURN == 10


def test_lead_max_steps_per_turn_is_twenty() -> None:
    assert LEAD_MAX_STEPS_PER_TURN == 20


def test_lead_cap_is_strictly_higher_than_chat_cap() -> None:
    assert LEAD_MAX_STEPS_PER_TURN > MAX_STEPS_PER_TURN
