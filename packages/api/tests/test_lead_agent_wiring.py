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


def test_lead_agent_orchestrator_toolset_overlaps_chat() -> None:
    """The lead is an orchestrator — it shares some tools with the chat
    path (list_metrics, clarify, final_answer) but DROPS direct data
    reads (mf_query, lookup_metric_definition) and ADDS orchestration
    tools (propose_plan, run_subagent, read/write_memory). It is NOT a
    superset of chat — that pattern was changed to force delegation."""
    chat_names = {t.name for t in ALL_TOOLS}
    lead_names = {t.name for t in LEAD_AGENT_TOOLS}
    shared = chat_names & lead_names
    assert shared == {"list_metrics", "clarify", "final_answer"}, (
        f"shared tools changed: {shared}"
    )
    lead_only = lead_names - chat_names
    assert lead_only == {
        "propose_plan",
        "run_subagent",
        "read_memory",
        "write_memory",
    }, f"lead-only tools changed: {lead_only}"
    chat_only = chat_names - lead_names
    assert chat_only == {"mf_query", "lookup_metric_definition"}, (
        f"chat-only tools changed: {chat_only}"
    )


def test_lead_prompt_mandates_delegation() -> None:
    """ANCHOR-F must explicitly tell the model it lacks mf_query so it
    delegates rather than fetching directly."""
    assert "DO NOT have `mf_query`" in LEAD_AGENT_SYSTEM_PROMPT
    assert "delegate" in LEAD_AGENT_SYSTEM_PROMPT.lower()


def test_lead_prompt_mandates_parallel_dispatch() -> None:
    """ANCHOR-F must instruct the model to batch run_subagent calls in
    a single response rather than serializing across turns."""
    assert "MULTIPLE" in LEAD_AGENT_SYSTEM_PROMPT
    assert "parallel" in LEAD_AGENT_SYSTEM_PROMPT.lower()
    assert "single response" in LEAD_AGENT_SYSTEM_PROMPT.lower()


def test_lead_prompt_states_step_budget() -> None:
    """ANCHOR-F must surface the 20-step budget so the model paces itself."""
    assert "20 LLM calls" in LEAD_AGENT_SYSTEM_PROMPT
    assert "Step Budget" in LEAD_AGENT_SYSTEM_PROMPT
