"""Single-LLM factory (HUG-190 Phase E, 2026-05-06).

Single source of truth for constructing the agent's `BaseChatModel`.
ONE provider at a time, no fallback chain (per user directive
2026-05-06). To switch providers, edit `config/llm.yaml`.

Usage:

    from nl_engine.llm import make_llm
    llm = make_llm()

Resolution order:

1. `config/llm.yaml` at the repo root (production source of truth).
2. Env vars (`LLM_PROVIDER`, `LLM_MODEL`) — for tests and local
   overrides without touching the file.
3. Tests can pass an explicit `LLMConfig` to `make_llm()` to bypass
   both.

Provider env vars:

* `groq`   → `GROQ_API_KEY`,   default model `qwen/qwen3-32b` (ADR-0004).
* `google` → `GOOGLE_API_KEY`, default model `gemma-4-31b-it`.
* `ollama` → `OLLAMA_API_KEY`, default model `qwen3-coder:480b`,
             optional `OLLAMA_BASE_URL` (default `https://ollama.com`).

ADR-0004 invariants are enforced inside `providers.groq` (temperature=0,
reasoning_format="hidden"). Other providers run at temperature=0 for
deterministic tool-calling.
"""

from nl_engine.llm.factory import LLMConfig, Role, make_llm

__all__ = ["LLMConfig", "Role", "make_llm"]
