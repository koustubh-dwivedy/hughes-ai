"""LangChain-compatible adapter around the Cerebras chat completions
endpoint already used by `nl_engine.engine`.

Wraps the synchronous Cerebras SDK so LangGraph can call it via the
`BaseChatModel` interface. Streaming + true async are deferred — the
agent_runner runs the graph in a thread executor so blocking calls
don't stall the event loop.
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Sequence
from typing import Any

from cerebras.cloud.sdk import Cerebras, RateLimitError
from cerebras.cloud.sdk.types.chat.chat_completion import ChatCompletionResponse
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

log = logging.getLogger(__name__)

_MODEL = "qwen-3-235b-a22b-instruct-2507"
_MODEL_FALLBACK = "llama3.1-8b"
_MIN_CALL_GAP = 13.0
_last_call_time = 0.0


def _rate_limit_wait() -> None:
    global _last_call_time
    gap = time.monotonic() - _last_call_time
    if gap < _MIN_CALL_GAP:
        time.sleep(_MIN_CALL_GAP - gap)
    _last_call_time = time.monotonic()


def _to_cerebras(messages: list[BaseMessage]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for m in messages:
        if isinstance(m, HumanMessage):
            out.append({"role": "user", "content": str(m.content)})
        elif isinstance(m, AIMessage):
            out.append({"role": "assistant", "content": str(m.content) or ""})
        elif isinstance(m, ToolMessage):
            out.append({"role": "tool", "content": str(m.content)})
        else:
            out.append({"role": "system", "content": str(m.content)})
    return out


class CerebrasChatModel(BaseChatModel):
    """Minimal BaseChatModel that delegates to Cerebras and parses the
    response into AIMessage with tool_calls when JSON-mode emits them."""

    tools: list[Any] = []

    @property
    def _llm_type(self) -> str:
        return "cerebras-chat-model"

    def bind_tools(
        self,
        tools: Sequence[Any],
        **kwargs: Any,
    ) -> CerebrasChatModel:
        return CerebrasChatModel(tools=list(tools))

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        api_key = os.environ.get("CEREBRAS_API_KEY")
        if not api_key:
            raise RuntimeError("CEREBRAS_API_KEY is not set")
        client = Cerebras(api_key=api_key)
        _rate_limit_wait()
        text = _call_cerebras(client, _to_cerebras(messages))
        return ChatResult(generations=[ChatGeneration(message=_parse_response(text))])


def _call_cerebras(client: Cerebras, msgs: list[dict[str, str]]) -> str:
    """Send `msgs` to Cerebras with a primary→fallback model fan-out."""
    try:
        resp = client.chat.completions.create(
            model=_MODEL,
            messages=msgs,  # type: ignore[arg-type]
            response_format={"type": "json_object"},
        )
    except RateLimitError:
        resp = client.chat.completions.create(
            model=_MODEL_FALLBACK,
            messages=msgs,  # type: ignore[arg-type]
            response_format={"type": "json_object"},
        )
    if not isinstance(resp, ChatCompletionResponse):
        raise RuntimeError(f"unexpected Cerebras response type: {type(resp)}")
    return resp.choices[0].message.content or "{}"


def _parse_response(text: str) -> AIMessage:
    """Parse Cerebras's JSON-mode response. If it has a `tool` field,
    emit an AIMessage with tool_calls; otherwise emit a plain assistant
    message with the JSON's `content` (or the raw text)."""
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return AIMessage(content=text)
    if isinstance(obj, dict) and "tool" in obj:
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": str(obj["tool"]),
                    "args": obj.get("args") or {},
                    "id": obj.get("id") or "call",
                }
            ],
        )
    if isinstance(obj, dict) and "content" in obj:
        return AIMessage(content=str(obj["content"]))
    return AIMessage(content=text)
