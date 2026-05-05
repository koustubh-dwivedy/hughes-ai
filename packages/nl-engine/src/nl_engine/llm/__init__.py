"""Multi-provider LLM factory (HUG-196).

Single source of truth for constructing the agent's `BaseChatModel`.
Replaces the duplicated construction in `api.services.llm.make_agent_llm`
and `nl-engine/benchmarks/run_eval.py:_make_eval_llm`.

Usage:

    from nl_engine.llm import make_llm
    llm = make_llm()

Environment variables read by `make_llm`:

* `LLM_PROVIDER` — `groq` (default) | `google`. Picks the primary provider.
* `LLM_FALLBACK_PROVIDER` — unset (default) | `groq` | `google`. When set,
  the factory wraps the primary in a `FallbackChatModel` that retries on
  rate-limit errors against the fallback.
* `LLM_MODEL` — optional model-ID override. Defaults per provider:
  - groq → `qwen/qwen3-32b` (per ADR-0004)
  - google → `gemma-4-31b-it`
* Provider credentials: `GROQ_API_KEY`, `GOOGLE_API_KEY`.

ADR-0004 invariants are enforced inside `providers.groq` (temperature=0,
reasoning_format="hidden"). `providers.google` mirrors the same temperature
default for consistency.
"""

from nl_engine.llm.factory import LLMConfig, make_llm

__all__ = ["LLMConfig", "make_llm"]
