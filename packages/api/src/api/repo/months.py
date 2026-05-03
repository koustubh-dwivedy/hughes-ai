"""Available-months queries per dashboard surface.

Pre-formed SQL keyed by surface keeps the read-only safety mechanically
obvious to lint: no f-string SQL, no table-name interpolation.
"""

from datetime import date

from api.repo.dashboards import fetch_mart_rows

_AVAILABLE_MONTHS_SQL: dict[str, str] = {
    "executive": (
        "SELECT DISTINCT as_of_month AS m FROM fct_executive_kpis "
        "ORDER BY m DESC"
    ),
    "deposits": (
        "SELECT DISTINCT as_of_month AS m FROM fct_deposits_monthly "
        "ORDER BY m DESC"
    ),
    "past-due": (
        "SELECT DISTINCT as_of_month AS m FROM fct_delinquency_monthly "
        "ORDER BY m DESC"
    ),
    "officer-branch": (
        "SELECT DISTINCT as_of_month AS m FROM fct_loans_monthly "
        "ORDER BY m DESC"
    ),
}


def fetch_available_months(surface: str, db_url: str) -> list[date]:
    """Return distinct as_of_month values for a surface, newest first."""
    sql = _AVAILABLE_MONTHS_SQL.get(surface)
    if sql is None:
        return []
    rows = fetch_mart_rows(sql, (), db_url)
    return [r["m"] for r in rows]
