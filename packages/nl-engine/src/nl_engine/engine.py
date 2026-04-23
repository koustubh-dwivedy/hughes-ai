"""NL→SQL pipeline: question → context → Gemma 4 → validate → execute → answer."""

import json
import os
from dataclasses import dataclass

import google.genai as genai
import google.genai.types as gtypes

from nl_engine.context_loader import AllContext
from nl_engine.context_selector import ContextSelector, SelectedContext
from nl_engine.executor import execute_sql
from nl_engine.sql_validator import validate_sql
from nl_engine.telemetry import span_stage

_MODEL = "gemma-4-26b-a4b-it"

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


@span_stage("select_context")
def _select_context(selector: ContextSelector, question: str) -> SelectedContext:
    return selector.select(question)


@span_stage("call_llm")
def _call_llm(system_prompt: str, question: str) -> dict[str, object]:
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    response = client.models.generate_content(
        model=_MODEL,
        contents=question,
        config=gtypes.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
        ),
    )
    text = response.text
    if text is None:
        raise ValueError("Empty LLM response")
    parsed: object = json.loads(text)
    if isinstance(parsed, list):
        parsed = parsed[0] if parsed else {}
    if not isinstance(parsed, dict):
        raise ValueError(f"Unexpected LLM response shape: {type(parsed)}")
    result: dict[str, object] = parsed
    return result


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
    question: str, db_url: str, ctx: AllContext
) -> AnswerResponse | ClarificationResponse:
    """Run the full NL→SQL pipeline. Raises SQLValidationError on unsafe SQL."""
    selector = ContextSelector(ctx)
    selected = _select_context(selector, question)
    if not selected.relevant_tables:
        return ClarificationResponse(
            question="Could you clarify which aspect of lending you're asking about?"
        )
    if _is_ambiguous(selected):
        return _ambiguity_clarification(selected)
    system_prompt = _build_system_prompt(selected)
    raw = _call_llm(system_prompt, question)
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
