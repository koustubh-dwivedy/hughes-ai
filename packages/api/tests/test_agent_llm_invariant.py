"""ADR-0004 invariant: the agent's LLM factory MUST pin
`reasoning_format="hidden"` so Qwen 3's chain-of-thought never leaks into
tool-call JSON. Failing this is a silent agent accuracy regression."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _set_groq_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """ChatGroq's constructor validates GROQ_API_KEY is present even
    when no call is made; set a dummy so the factory can instantiate."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key")


def test_make_agent_llm_pins_reasoning_format_hidden() -> None:
    from api.services.llm import make_agent_llm

    llm = make_agent_llm()
    reasoning = getattr(llm, "reasoning_format", None)
    assert reasoning == "hidden", (
        f"make_agent_llm() did not pin reasoning_format='hidden' "
        f"(saw {reasoning!r}). "
        "This is the ADR-0004 invariant — see services/llm.py docstring."
    )


def test_make_agent_llm_uses_qwen_32b() -> None:
    from api.services.llm import make_agent_llm

    llm = make_agent_llm()
    model_name = getattr(llm, "model_name", None) or getattr(llm, "model", None)
    assert "qwen/qwen3-32b" in str(model_name), (
        f"make_agent_llm() should use qwen/qwen3-32b, saw {model_name}"
    )
