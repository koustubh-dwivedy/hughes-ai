"""ADR-0004 invariant: every Groq call site in nl_engine.engine MUST pass
`reasoning_format="hidden"`.

Without this kwarg, Qwen 3's chain-of-thought leaks into the JSON-mode
response and breaks downstream parsing. Failing this test means a
silent accuracy regression in production. Do not relax it.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _set_groq_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-key")


def test_engine_passes_reasoning_format_hidden() -> None:
    """The engine's _create() must pass reasoning_format='hidden' on every call."""
    from nl_engine.engine import _create

    fake_client = MagicMock()
    fake_response = MagicMock()
    fake_response.choices = [MagicMock(message=MagicMock(content='{"sql": "X"}'))]
    fake_response.usage = MagicMock(total_tokens=10)
    fake_response.model = "qwen/qwen3-32b"
    fake_client.chat.completions.create.return_value = fake_response

    with patch("nl_engine.engine.ChatCompletion", new=type(fake_response)):
        _create(fake_client, "qwen/qwen3-32b", "sys", "q")

    kwargs = fake_client.chat.completions.create.call_args.kwargs
    assert kwargs.get("reasoning_format") == "hidden", (
        f"engine._create() did not pass reasoning_format='hidden' "
        f"(saw kwargs={list(kwargs.keys())}). "
        "This is the ADR-0004 invariant — see the module docstring."
    )
