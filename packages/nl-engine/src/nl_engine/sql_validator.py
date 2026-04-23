"""sqlglot AST validator: SELECT-only, tables/columns must be in the allowlist."""

import sqlglot
import sqlglot.errors
from sqlglot import exp as sqlglot_exp

from nl_engine.context_selector import SelectedContext


class SQLValidationError(Exception):
    pass


def validate_sql(sql: str, ctx: SelectedContext) -> None:
    """Raise SQLValidationError if sql is not a safe SELECT over allowlisted schema."""
    try:
        ast = sqlglot.parse_one(sql, dialect="postgres")
    except sqlglot.errors.ParseError as exc:
        raise SQLValidationError("Parse error: " + str(exc)) from exc

    if ast.key != "select":
        raise SQLValidationError(
            "Only SELECT is allowed; got " + ast.key.upper()
        )

    allowed_tables = {t.name for t in ctx.relevant_tables}
    allowed_columns = {c.name for c in ctx.relevant_columns}

    for table in ast.find_all(sqlglot_exp.Table):
        if table.name and table.name not in allowed_tables:
            raise SQLValidationError(
                "Table '" + table.name + "' is not in the allowlist"
            )

    for col in ast.find_all(sqlglot_exp.Column):
        if col.name and col.name not in allowed_columns:
            raise SQLValidationError(
                "Column '" + col.name + "' is not in the allowlist"
            )
