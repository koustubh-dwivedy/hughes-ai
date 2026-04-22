"""Load and validate the four NL engine context YAML files at startup."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ValidationError

_CONTEXT_DIR = Path(__file__).parents[2] / "context"


class ContextValidationError(Exception):
    def __init__(self, source: str, detail: str) -> None:
        self.source = source
        self.detail = detail
        super().__init__(f"{source}: {detail}")


# ---------------------------------------------------------------------------
# schema_context.yaml models
# ---------------------------------------------------------------------------


class Column(BaseModel):
    name: str
    type: str
    description: str
    example: str


class Table(BaseModel):
    name: str
    description: str
    columns: list[Column]


# ---------------------------------------------------------------------------
# metrics.yaml models
# ---------------------------------------------------------------------------


class Metric(BaseModel):
    name: str
    label: str
    description: str
    formula_plain_english: str
    caveats: str
    related_questions: list[str]


# ---------------------------------------------------------------------------
# rules.yaml models
# ---------------------------------------------------------------------------


class Rule(BaseModel):
    id: str
    rule: str
    rationale: str


# ---------------------------------------------------------------------------
# examples.yaml models
# ---------------------------------------------------------------------------


class Example(BaseModel):
    question: str
    sql: str
    notes: str = ""


# ---------------------------------------------------------------------------
# Top-level container
# ---------------------------------------------------------------------------


class AllContext(BaseModel):
    tables: list[Table]
    metrics: list[Metric]
    rules: list[Rule]
    examples: list[Example]


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def _load_yaml(filename: str) -> Any:
    path = _CONTEXT_DIR / filename
    with path.open() as fh:
        return yaml.safe_load(fh)


def _parse(model_cls: type, data: Any, source: str) -> Any:
    try:
        return model_cls(**data)
    except (ValidationError, TypeError) as exc:
        raise ContextValidationError(source, str(exc)) from exc


def _parse_list(model_cls: type, items: list[Any], source: str) -> list[Any]:
    try:
        return [_parse(model_cls, item, source) for item in items]
    except ContextValidationError:
        raise
    except Exception as exc:
        raise ContextValidationError(source, str(exc)) from exc


def load_all() -> AllContext:
    """Load and validate all four context YAML files.

    Raises ContextValidationError (not raw Pydantic error) on invalid YAML,
    identifying the specific file and missing/invalid field.
    """
    schema_raw = _load_yaml("schema_context.yaml")
    metrics_raw = _load_yaml("metrics.yaml")
    rules_raw = _load_yaml("rules.yaml")
    examples_raw = _load_yaml("examples.yaml")

    return AllContext(
        tables=_parse_list(
            Table, schema_raw.get("tables", []), "schema_context.yaml"
        ),
        metrics=_parse_list(
            Metric, metrics_raw.get("metrics", []), "metrics.yaml"
        ),
        rules=_parse_list(Rule, rules_raw.get("rules", []), "rules.yaml"),
        examples=_parse_list(
            Example, examples_raw.get("examples", []), "examples.yaml"
        ),
    )
