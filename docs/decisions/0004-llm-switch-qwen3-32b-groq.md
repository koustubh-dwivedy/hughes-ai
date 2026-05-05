# ADR-0004: LLM switch — Qwen 3 32B on Groq Cloud

**Date:** 2026-05-05
**Status:** Accepted
**Linear epic:** HUG-172
**Linear issue:** HUG-182
**Supersedes:** ADR-0003 Decision #8 (Qwen 3 235B on Cerebras)

---

## Context

ADR-0003 (locked 2026-05-05 02:09 UTC) chose Qwen 3 235B on Cerebras for both the legacy `engine.ask()` one-shot pipeline and the new LangGraph ReAct agent. Five hours later, the first end-to-end run of the NL accuracy benchmark scored 28/70 (40%) against an 85% gate.

Three operational facts surfaced after that run that argue for a different LLM provider:

1. **Cerebras 5-req/min ceiling is hostile to multi-turn ReAct.** The agent averages 2–3 LLM calls per turn and is capped at 10. At 5 RPM, a single user with a 5-call turn locks the rate-limit budget for a full minute, which makes both the eval (50–70 questions × 3–10 calls) and any real conversational load economically unworkable.
2. **The legacy 13-second `_MIN_CALL_GAP` global lock in `engine.py`** that papers over the Cerebras limit will not survive multi-turn — a process-wide blocking sleep is the wrong primitive for a tool-calling loop. Removing it requires a provider with real headroom.
3. **The Qwen 3 32B model on Groq is well-matched to our actual workload.** We are not doing reasoning that demands the 235B's extra capacity; we are doing constrained tool calling against a 38-metric MetricFlow catalog. A smaller, faster, cheaper model with native function calling is the right shape.

The user (Koustubh) has decided to switch the LLM stack across both `engine.ask()` and the agent.

## Decision

| Aspect | Choice |
|---|---|
| Provider | **Groq Cloud** |
| Model | **`qwen/qwen3-32b`** (Qwen 3, 32B parameters, instruction-tuned) |
| Tool calling | Native, OpenAI-compatible (`tools=[...]`, `tool_choice="auto"`) |
| SDK (agent) | `langchain-groq.ChatGroq` — drop-in via `bind_tools()` for our existing LangGraph agent |
| SDK (engine) | `groq.Groq` (synchronous, OpenAI-compatible) for the direct `engine.ask` call |
| Env var | `GROQ_API_KEY` (replaces `CEREBRAS_API_KEY`) |
| Reasoning mode | `reasoning_format="hidden"` on every call — **mandatory** |
| Structured output | `response_format={"type": "json_object"}` for the engine; agent relies on tool-call parsing |
| Rate limit (dev tier) | 60 RPM, 6K TPM (12× Cerebras headroom on requests) |
| Pricing | $0.29 / 1M input, $0.59 / 1M output (~$0.44 blended); ≈$1–2 per full-eval batch |
| Context | 131K tokens; 40K max output |
| Fallback (documented, not shipped) | `qwen/qwen3-235b-a22b-instruct-2507` on Groq, same SDK, higher cost — only enabled if HUG-190 evals show category-specific gaps the 32B can't close |

The migration covers **both** `engine.ask()` (legacy `/ask`) and the LangGraph agent (`/threads`). ADR-0003 Decision #2 (`/ask` stays as a stateless one-shot) still holds — `/ask` is preserved for back-compat, just on the new model.

## Why these choices

### Why Qwen 3 32B over a different model on Groq
We're already invested in Qwen's prompt patterns (the system prompts in `engine.py` and the agent's tool instructions are tuned for Qwen 3 family conventions, including `/think` toggle semantics). Qwen 3 32B is the smallest member of the family that retains strong native function calling, which is the operation our agent does on every step. Llama 3.3 70B and Mixtral were rejected: Llama for weaker function calling on smaller variants, Mixtral for being EOL on Groq.

### Why Groq over Cerebras / Together / Fireworks
Groq's dev-tier 60 RPM eliminates the rate-limit gymnastics that ADR-0003 acknowledged as Risk #1 — multi-turn ReAct becomes feasible without a process-wide lock or token-bucket throttle. Speed (~400–535 tokens/sec on Groq's hardware) is a free bonus; the 32B model returns full responses faster than the 235B does on Cerebras even ignoring the rate limit. Pricing is favourable ($0.44/1M blended vs $3+/1M for Claude, $0.5+/1M for Cerebras 235B).

### Why `reasoning_format="hidden"` is non-negotiable
Qwen 3 supports a chain-of-thought (`/think`) mode. When enabled — and on Groq it can be toggled per-request via `reasoning_format` — the model emits its reasoning in the response. **If `reasoning_format` is not explicitly `"hidden"`, the reasoning text leaks into the assistant message content and corrupts our tool-call JSON parser.** The mode flag is a hard requirement, not a knob. Enforced by a unit test in HUG-183 that asserts every Groq call site passes this kwarg.

### Why `langchain-groq` for the agent and raw `groq` for the engine
The agent already lives behind LangChain's `BaseChatModel` interface (`packages/api/src/api/services/llm.py`). `ChatGroq` from `langchain-groq` is a complete drop-in — `bind_tools()` works, message conversion is handled, async + sync are both supported. The legacy `engine.ask()` is one synchronous call to a chat completion API; pulling in LangChain there would be ceremony for no value. Two SDKs, but each one is the natural fit for its caller and they share the same auth surface (`GROQ_API_KEY`).

### Why we don't preemptively use a fallback model
Qwen 3 32B is materially smaller than 235B. We accept that some hard categories may regress; the response is to add few-shot examples and per-category prompt tuning in HUG-190, not to silently route to a bigger model. If after HUG-190 a specific category remains stuck below the must-pass gate, the documented escalation is to add `qwen/qwen3-235b-a22b-instruct-2507` as a category-conditional fallback (same SDK, same `bind_tools()`, ~3× cost). Not before.

### Why structured output via `json_object` only
Groq supports OpenAI-style strict `response_format={"type": "json_schema", ...}` only for GPT-OSS models. Qwen 3 32B is limited to `{"type": "json_object"}` (free-form JSON, no schema enforcement). This is fine for our design: the engine's expected output shape is small and well-described in the system prompt; the agent's typed contract is enforced by tool-call schemas, not by `response_format`.

## Consequences

- **`cerebras-cloud-sdk` is removed** from `packages/nl-engine/pyproject.toml` and `packages/api/pyproject.toml`.
- **`CEREBRAS_API_KEY` is removed** from `.env.example` and from both CI workflows (`ci.yml`, `nl-eval.yml`); `GROQ_API_KEY` takes its place. Adding the secret to GitHub repo settings is a user action.
- **The 13-second `_MIN_CALL_GAP` lock in `engine.py` goes away.** Replaced by per-call retry/backoff via `tenacity` only if eval bursts past Groq's TPM ceiling.
- **The 40% baseline measured under Cerebras Qwen 3 235B is no longer apples-to-apples.** First action of HUG-190 is to re-baseline on Groq + Qwen 3 32B before any prompt tuning, so we know which improvements come from the model and which from the eval rewrites.
- **Memory file `project_llm_switch.md`** (which had been describing the obsolete Apr 23 Gemma experiment) is rewritten in this same commit to reflect the Qwen 3 32B (Groq) ground truth.
- **CLAUDE.md** repo-map is updated to read "Qwen 3 32B (Groq)" instead of the prior Cerebras line.
- **ADR-0003 stays as-is** with a "Superseded by ADR-0004 (2026-05-05)" note appended to Decision #8. The original locked decision is preserved for audit.

## References

- Groq model catalog — https://console.groq.com/docs/models
- Qwen 3 32B model card on Groq — https://console.groq.com/docs/model/qwen/qwen3-32b
- Groq tool-use docs — https://console.groq.com/docs/tool-use/overview
- Groq structured outputs (notes the json_schema gap) — https://console.groq.com/docs/structured-outputs
- LangChain Groq integration — https://docs.langchain.com/oss/python/integrations/chat/groq
- `langchain-groq` PyPI — https://pypi.org/project/langchain-groq/
- ADR-0003 (the predecessor) — `docs/decisions/0003-data-intelligence-v2.md`
