"""Two-provider fallback chain.

Wraps a primary `BaseChatModel` and falls through to a fallback model
when the primary raises a rate-limit-shaped exception. Logs every
fallback occurrence at WARNING level so silent provider switches are
visible in dev/CI logs.

Detection rule: catches exceptions whose string representation contains
HTTP status `429` OR a token/quota substring. Both Groq and Google AI
Studio surface rate-limits via 429 responses with descriptive messages.

Non-rate-limit errors (e.g., auth, network, malformed prompt) propagate
unchanged from the primary — fallback only triggers on explicit quota /
rate-limit signals so transient bugs don't silently cross-providers.
"""

from __future__ import annotations

import logging
from typing import Any, cast

from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from langchain_core.tools import BaseTool

log = logging.getLogger(__name__)

_RATE_LIMIT_MARKERS = (
    "429",
    "rate_limit",
    "rate limit",
    "quota",
    "tokens per day",
    "tpd",
    "tpm",
)


def _is_rate_limit_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return any(marker in msg for marker in _RATE_LIMIT_MARKERS)


class FallbackChatModel(BaseChatModel):
    """`BaseChatModel` that tries `primary` first, falls back to `fallback`
    on rate-limit errors. Tools bound on this wrapper are bound to BOTH
    underlying models so the fallback path keeps the same tool signature.
    """

    primary: BaseChatModel
    fallback: BaseChatModel

    @property
    def _llm_type(self) -> str:
        return "fallback-chat-model"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        try:
            return self.primary._generate(
                messages, stop=stop, run_manager=run_manager, **kwargs,
            )
        except Exception as exc:  # noqa: BLE001
            if not _is_rate_limit_error(exc):
                raise
            log.warning(
                "primary LLM rate-limited; falling back: %s",
                str(exc)[:200],
            )
            return self.fallback._generate(
                messages, stop=stop, run_manager=run_manager, **kwargs,
            )

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        try:
            return await self.primary._agenerate(
                messages, stop=stop, run_manager=run_manager, **kwargs,
            )
        except Exception as exc:  # noqa: BLE001
            if not _is_rate_limit_error(exc):
                raise
            log.warning(
                "primary LLM rate-limited; falling back: %s",
                str(exc)[:200],
            )
            return await self.fallback._agenerate(
                messages, stop=stop, run_manager=run_manager, **kwargs,
            )

    def bind_tools(  # type: ignore[override]
        self,
        tools: list[BaseTool] | list[dict[str, Any]] | list[Any],
        **kwargs: Any,
    ) -> FallbackChatModel:
        """Bind tools to BOTH the primary and the fallback so the chain
        behaves identically end-to-end regardless of which provider serves
        the actual call.
        """
        # bind_tools returns a Runnable that still implements BaseChatModel's
        # _generate interface; cast to satisfy the dataclass field type.
        bound_primary = cast(BaseChatModel, self.primary.bind_tools(tools, **kwargs))
        bound_fallback = cast(BaseChatModel, self.fallback.bind_tools(tools, **kwargs))
        return FallbackChatModel(primary=bound_primary, fallback=bound_fallback)
