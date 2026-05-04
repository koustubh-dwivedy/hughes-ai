"""Fake chat model that emits a scripted sequence of messages.

Lets the tests drive the LangGraph orchestrator deterministically
without ever calling Cerebras / Qwen 3.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class FakeChatModel(BaseChatModel):
    """Returns the next pre-scripted AIMessage on every invoke()."""

    responses: list[AIMessage]
    call_count: int = 0

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        if self.call_count >= len(self.responses):
            # Re-emit the last response — useful for step-cap tests where
            # we want an unending tool-call loop.
            response = self.responses[-1]
        else:
            response = self.responses[self.call_count]
        self.call_count += 1
        return ChatResult(generations=[ChatGeneration(message=response)])

    @property
    def _llm_type(self) -> str:
        return "fake-chat-model"

    def bind_tools(  # type: ignore[override]
        self,
        tools: Sequence[Any],
        **kwargs: Any,
    ) -> FakeChatModel:
        # The fake doesn't need to know about tools — its responses are
        # already pre-scripted with tool_calls baked in.
        return self
