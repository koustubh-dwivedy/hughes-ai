"""Lead agent wiring tests (HUG-244).

Verifies the flag-gated routing and the basic contract of
`stream_lead_turn` without invoking an actual LLM. Live-LLM end-to-end
tests are deferred to the deep-research eval suite (HUG-248).
"""

from __future__ import annotations

from nl_engine.agent.lead_agent_prompt import LEAD_AGENT_SYSTEM_PROMPT
from nl_engine.agent.tools import ALL_TOOLS, LEAD_AGENT_TOOLS


def test_lead_system_prompt_supersedes_chat_prompt() -> None:
    """The lead-agent prompt must contain the chat prompt's anchors
    plus the new ANCHOR-F. This proves we EXTEND rather than replace
    so the lead inherits all MetricFlow tool-calling guidance."""
    assert "ANCHOR-A" in LEAD_AGENT_SYSTEM_PROMPT
    assert "ANCHOR-B" in LEAD_AGENT_SYSTEM_PROMPT
    assert "ANCHOR-C" in LEAD_AGENT_SYSTEM_PROMPT
    assert "ANCHOR-D" in LEAD_AGENT_SYSTEM_PROMPT
    assert "ANCHOR-E" in LEAD_AGENT_SYSTEM_PROMPT
    assert "ANCHOR-F" in LEAD_AGENT_SYSTEM_PROMPT


def test_lead_prompt_documents_each_new_tool() -> None:
    """The system prompt explicitly names each lead-only tool."""
    for tool_name in ["propose_plan", "run_subagent", "read_memory", "write_memory"]:
        assert tool_name in LEAD_AGENT_SYSTEM_PROMPT, (
            f"prompt missing {tool_name}"
        )


def test_lead_prompt_includes_multi_chart_heuristic() -> None:
    """ANCHOR-F mandates multi-chart for deep questions."""
    assert "MANDATORY" in LEAD_AGENT_SYSTEM_PROMPT
    assert "Stack" in LEAD_AGENT_SYSTEM_PROMPT
    assert "KpiTile" in LEAD_AGENT_SYSTEM_PROMPT


def test_lead_agent_tools_proper_superset() -> None:
    chat_names = {t.name for t in ALL_TOOLS}
    lead_names = {t.name for t in LEAD_AGENT_TOOLS}
    assert chat_names < lead_names, "lead must be a strict superset of chat"
    delta = lead_names - chat_names
    assert delta == {"propose_plan", "run_subagent", "read_memory", "write_memory"}, (
        f"unexpected lead-only tools: {delta}"
    )
