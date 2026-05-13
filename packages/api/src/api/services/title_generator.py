"""ChatGPT-style thread-title generation.

Given the user's first message in a thread, ask the LLM to produce a
3-6 word sidebar title. Falls back to a deterministic first-N-words
truncation if the LLM raises or returns something unusable.

Called fire-and-forget from `/threads/{id}/messages` (see
`api.routes.threads`) and from the one-off backfill script
`scripts/backfill_thread_titles.py`. The repo-level
`update_thread_title` SQL is conditional on `title IS NULL`, so
concurrent fire is idempotent.
"""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from api.logging import get_logger

_TITLE_SYSTEM_PROMPT = (
    "You generate short sidebar titles for a chat application, like"
    " ChatGPT does. Given the user's question, output a 3-6 word title"
    " that summarizes what the conversation is about. Rules:"
    " no surrounding quotes; no trailing period; no leading prefix"
    " like 'Q:' or 'Title:'. Title only, nothing else."
)

_MAX_TITLE_CHARS = 60
_FALLBACK_WORDS = 6


def _fallback_title(user_message: str) -> str:
    """Deterministic truncation used when the LLM call fails or returns
    unusable output. Takes the first `_FALLBACK_WORDS` words."""
    cleaned = (user_message or "").strip()
    if not cleaned:
        return "Untitled chat"
    words = cleaned.split()[:_FALLBACK_WORDS]
    title = " ".join(words)
    if len(title) > _MAX_TITLE_CHARS:
        title = title[: _MAX_TITLE_CHARS - 1].rstrip() + "…"
    return title


def _sanitize(raw: str) -> str:
    """Strip wrapping quotes, trailing period, surrounding whitespace."""
    title = raw.strip()
    # Drop leading "Title:" / "Q:" prefixes the LLM sometimes adds.
    for prefix in ("Title:", "title:", "Q:", "Question:"):
        if title.startswith(prefix):
            title = title[len(prefix):].strip()
    # Strip wrapping quotes (curly or straight).
    for q in ('"', "'", "“", "”", "‘", "’"):
        if title.startswith(q) and title.endswith(q):
            title = title[1:-1].strip()
    # Drop a single trailing period (but keep "..." / "…").
    if title.endswith(".") and not title.endswith(("..", "…")):
        title = title[:-1]
    return title.strip()


def generate_title(user_message: str, llm: BaseChatModel) -> str:
    """Generate a sidebar title for a thread.

    Falls back to `_fallback_title(user_message)` if the LLM raises or
    returns something obviously unusable (empty, too long, multi-line).
    Always returns a non-empty string ≤ 60 chars.
    """
    slog = get_logger().bind(component="api.title_generator")
    cleaned_input = (user_message or "").strip()
    if not cleaned_input:
        return _fallback_title(cleaned_input)
    try:
        result = llm.invoke(
            [
                SystemMessage(content=_TITLE_SYSTEM_PROMPT),
                HumanMessage(content=cleaned_input),
            ]
        )
        raw = getattr(result, "content", None) or ""
        if isinstance(raw, list):
            # Some chat models return content as a list of parts.
            raw = " ".join(
                str(p.get("text", p)) if isinstance(p, dict) else str(p)
                for p in raw
            )
        title = _sanitize(str(raw))
        if not title or "\n" in title or len(title) > _MAX_TITLE_CHARS:
            slog.warning(
                "title_generator.fallback_used",
                reason="unusable_output",
                raw_len=len(str(raw)),
            )
            return _fallback_title(cleaned_input)
        return title
    except Exception as exc:  # noqa: BLE001 — surfaced as fallback
        slog.warning(
            "title_generator.fallback_used",
            reason="llm_exception",
            error_type=type(exc).__name__,
            error=str(exc)[:200],
        )
        return _fallback_title(cleaned_input)
