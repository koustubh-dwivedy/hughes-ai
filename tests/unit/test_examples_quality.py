"""Quality gate: example SQL parses with sqlglot; mart tables in schema_context."""
import sys
from pathlib import Path

import sqlglot
import sqlglot.expressions as exp

sys.path.insert(0, str(Path(__file__).parents[3] / "packages" / "nl-engine" / "src"))

from nl_engine.context_loader import load_all

_MART_PREFIXES = ("fct_", "dim_", "recon_")


def _ctx():
    return load_all()


def test_all_examples_sql_parses() -> None:
    errors = []
    for example in _ctx().examples:
        try:
            sqlglot.parse_one(example.sql, dialect="postgres")
        except sqlglot.errors.ParseError as exc:
            errors.append(f"Q: {example.question!r}: {exc}")
    assert not errors, "SQL parse errors:\n" + "\n".join(errors)


def test_mart_tables_in_schema_context() -> None:
    ctx = _ctx()
    schema_names = {t.name.lower() for t in ctx.tables}
    errors = []
    for example in ctx.examples:
        tree = sqlglot.parse_one(example.sql, dialect="postgres")
        for table in tree.find_all(exp.Table):
            name = (table.name or "").lower()
            is_mart = any(name.startswith(p) for p in _MART_PREFIXES)
            if is_mart and name not in schema_names:
                errors.append(
                    f"Q: {example.question!r} references undocumented"
                    f" mart table '{name}'"
                )
    assert not errors, "Undocumented mart tables:\n" + "\n".join(errors)
