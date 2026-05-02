"""NL→SQL pipeline: question → context → Qwen 3 (Cerebras) → validate → execute."""

import json
import os
import time
from dataclasses import dataclass

from cerebras.cloud.sdk import Cerebras, RateLimitError
from cerebras.cloud.sdk.types.chat.chat_completion import (
    ChatCompletionResponse,
)

from nl_engine.context_loader import AllContext
from nl_engine.context_selector import ContextSelector, SelectedContext
from nl_engine.executor import execute_sql
from nl_engine.sql_validator import validate_sql
from nl_engine.telemetry import get_tracer, span_stage

_MODEL = "qwen-3-235b-a22b-instruct-2507"
_MODEL_FALLBACK = "llama3.1-8b"

# 5 requests per minute — enforce a minimum gap between calls (13s gives
# ~4.6 req/min, leaving headroom for calls made outside this process)
_MIN_CALL_GAP = 13.0
_last_call_time: float = 0.0

_ROLE = (
    "You are a read-only SQL analyst for a credit union lending analytics "
    "system. You translate natural language questions into precise PostgreSQL "
    "SELECT statements grounded in the schema, metrics, and business rules "
    "provided below.\n\n"
    "IMPORTANT: You may ONLY reference the tables and columns listed in the "
    "schema below. Do NOT invent table or column names."
)

_JSON_FORMAT = (
    "Respond ONLY with a valid JSON object. "
    "No markdown fences, no prose outside JSON.\n"
    "Required fields:\n"
    '  "sql": string — a single PostgreSQL SELECT statement\n'
    '  "explanation": string — plain-English explanation of the query\n'
    '  "tables_used": array of strings — table names referenced in SQL\n'
    '  "assumptions": array of strings — assumptions made (empty if none)\n'
    '  "caveats": array of strings — business caveats the user should know\n'
)


@dataclass
class AnswerResponse:
    sql: str
    explanation: str
    tables_used: list[str]
    assumptions: list[str]
    caveats: list[str]
    rows: list[dict[str, object]]
    columns: list[str]


@dataclass
class ClarificationResponse:
    question: str


def _str_list(val: object) -> list[str]:
    return [str(v) for v in val] if isinstance(val, list) else []


def _fmt_tables(ctx: SelectedContext) -> str:
    parts = []
    for t in ctx.relevant_tables:
        cols = ", ".join(
            f"{c.name} ({c.type}): {c.description}" for c in t.columns
        )
        parts.append(f"Table {t.name}: {t.description}\n  Columns: {cols}")
    return "\n".join(parts)


def _fmt_metrics(ctx: SelectedContext) -> str:
    return "\n".join(
        f"- {m.label}: {m.formula_plain_english}. Caveat: {m.caveats}"
        for m in ctx.relevant_metrics
    )


def _fmt_examples(ctx: SelectedContext) -> str:
    return "\n\n".join(
        f"Q: {e.question}\nSQL: {e.sql.strip()}" for e in ctx.relevant_examples
    )


def _build_system_prompt(ctx: SelectedContext) -> str:
    sections = [_ROLE, "## Schema\n" + _fmt_tables(ctx)]
    if ctx.relevant_metrics:
        sections.append("## Metrics\n" + _fmt_metrics(ctx))
    if ctx.relevant_examples:
        sections.append("## Examples\n" + _fmt_examples(ctx))
    sections.append("## Output format\n" + _JSON_FORMAT)
    return "\n\n".join(sections)


def _is_ambiguous(selected: SelectedContext) -> bool:
    return len(selected.relevant_metrics) >= 2


def _ambiguity_clarification(selected: SelectedContext) -> ClarificationResponse:
    labels = [m.label for m in selected.relevant_metrics]
    options = ", ".join(labels[:-1]) + " or " + labels[-1]
    return ClarificationResponse(
        question="Your question could refer to multiple metrics: "
        + options
        + ". Which one are you asking about?"
    )


def _inject_metric_caveats(
    answer: AnswerResponse, selected: SelectedContext
) -> AnswerResponse:
    existing = set(answer.caveats)
    extra = [
        m.caveats
        for m in selected.relevant_metrics
        if m.caveats and m.caveats not in existing
    ]
    if extra:
        answer.caveats = answer.caveats + extra
    return answer


def _rate_limit_wait() -> None:
    """Enforce a minimum gap between calls to stay within 5 req/min."""
    global _last_call_time
    gap = time.monotonic() - _last_call_time
    if gap < _MIN_CALL_GAP:
        time.sleep(_MIN_CALL_GAP - gap)
    _last_call_time = time.monotonic()


@span_stage("select_context")
def _select_context(selector: ContextSelector, question: str) -> SelectedContext:
    return selector.select(question)


def _create(
    client: Cerebras, model: str, system_prompt: str, question: str
) -> ChatCompletionResponse:
    raw = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        response_format={"type": "json_object"},
    )
    if not isinstance(raw, ChatCompletionResponse):
        raise ValueError(f"Unexpected response type: {type(raw)}")
    return raw


@span_stage("call_llm")
def _call_llm(
    system_prompt: str, question: str
) -> tuple[dict[str, object], int | None, str]:
    _rate_limit_wait()
    api_key = os.environ.get("CEREBRAS_API_KEY")
    if not api_key:
        raise RuntimeError(
            "CEREBRAS_API_KEY is not set. Source .env or export the key "
            "before starting the API server."
        )
    client = Cerebras(api_key=api_key)
    # Primary: Qwen 235B. On RateLimitError fall back to llama3.1-8b,
    # then retry the fallback twice (60s, 120s) if the queue is still full.
    try:
        response = _create(client, _MODEL, system_prompt, question)
    except RateLimitError:
        for wait in [0, 60, 120]:
            if wait:
                time.sleep(wait)
            try:
                response = _create(client, _MODEL_FALLBACK, system_prompt, question)
                break
            except RateLimitError:
                continue
        else:
            raise ValueError("LLM unavailable after fallback retries")
    text = response.choices[0].message.content
    if text is None:
        raise ValueError("Empty LLM response")
    parsed: object = json.loads(text)
    if isinstance(parsed, list):
        parsed = parsed[0] if parsed else {}
    if not isinstance(parsed, dict):
        raise ValueError(f"Unexpected LLM response shape: {type(parsed)}")
    result: dict[str, object] = parsed
    total_tokens: int | None = None
    if response.usage and response.usage.total_tokens is not None:
        total_tokens = response.usage.total_tokens
    return result, total_tokens, response.model


@span_stage("validate_sql")
def _run_validation(raw: dict[str, object], ctx: SelectedContext) -> str:
    sql = str(raw["sql"])
    validate_sql(sql, ctx)
    return sql


@span_stage("execute_sql")
def _run_query(
    sql: str, db_url: str
) -> tuple[list[dict[str, object]], list[str]]:
    return execute_sql(sql, db_url)


def ask(
    question: str, db_url: str, ctx: AllContext, request_id: str = ""
) -> AnswerResponse | ClarificationResponse:
    """Run the full NL→SQL pipeline. Raises SQLValidationError on unsafe SQL."""
    tracer = get_tracer()
    with tracer.start_as_current_span("ask") as root_span:
        if request_id:
            root_span.set_attribute("request_id", request_id)
        selector = ContextSelector(ctx)
        selected = _select_context(selector, question)
        if not selected.relevant_tables:
            return ClarificationResponse(
                question=(
                    "Could you clarify which aspect of lending you're asking about?"
                )
            )
        if _is_ambiguous(selected):
            return _ambiguity_clarification(selected)
        system_prompt = _build_system_prompt(selected)
        raw, token_count, model_name = _call_llm(system_prompt, question)
        root_span.set_attribute("llm.token_count", token_count or 0)
        root_span.set_attribute("llm.model", model_name)
        sql = _run_validation(raw, selected)
        rows, columns = _run_query(sql, db_url)
        answer = AnswerResponse(
            sql=sql,
            explanation=str(raw.get("explanation", "")),
            tables_used=_str_list(raw.get("tables_used")),
            assumptions=_str_list(raw.get("assumptions")),
            caveats=_str_list(raw.get("caveats")),
            rows=rows,
            columns=columns,
        )
        return _inject_metric_caveats(answer, selected)
