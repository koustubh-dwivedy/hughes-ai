"""Keyword routing: maps a question to the relevant subset of context (allowlist)."""

from dataclasses import dataclass, field

from nl_engine.context_loader import AllContext, Column, Example, Metric, Table

# (keywords, table_names, metric_names, column_names)
_Route = tuple[list[str], list[str], list[str], list[str]]

_ROUTES: list[_Route] = [
    (
        ["origination", "originate", "originated", "how many loan",
         "loan count", "applications received", "new loan"],
        ["fct_loan_originations"],
        ["origination_volume"],
        [],
    ),
    (
        ["funded", "funding event", "disbursed"],
        ["fct_loan_originations"],
        ["origination_volume", "funding_rate"],
        ["funded_at", "funded_amount"],
    ),
    (
        ["approval", "approve", "approved", "declined", "underwriting",
         "credit decision"],
        ["fct_loan_originations", "recon_bridge"],
        ["approval_rate"],
        ["loan_status", "has_los_link", "has_symitar_link", "match_type", "created_at"],
    ),
    (
        ["funding rate", "pull-through", "pull through", "pullthrough"],
        ["fct_loan_originations", "recon_bridge"],
        ["funding_rate"],
        ["has_los_link", "has_symitar_link", "created_at"],
    ),
    (
        ["average loan", "avg loan", "loan amount", "loan size", "mean loan"],
        ["fct_loan_originations"],
        ["avg_loan_amount"],
        ["funded_amount", "requested_amount"],
    ),
    (
        ["portfolio", "balance", "outstanding", "total balance"],
        ["fct_loan_performance"],
        ["portfolio_balance"],
        ["balance", "snapshot_date"],
    ),
    (
        ["delinquent", "delinquency", "past due", "dpd", "overdue",
         "30 day", "60 day", "90 day"],
        ["fct_loan_performance"],
        ["delinquency_rate"],
        ["days_past_due", "is_delinquent", "delinquency_bucket", "snapshot_date"],
    ),
    (
        ["branch", "location", "region"],
        ["fct_loan_originations", "dim_loan"],
        [],
        ["branch_name", "branch_region"],
    ),
    (
        ["channel", "online", "mobile", "dealer", "broker"],
        ["fct_loan_originations", "dim_loan"],
        [],
        ["channel"],
    ),
    (
        ["product type", "product", "auto", "personal", "mortgage"],
        ["fct_loan_originations", "dim_loan"],
        [],
        ["product_type"],
    ),
    (
        ["reconciliation", "reconcile", "unmatched", "match rate", "los match"],
        ["recon_bridge"],
        [],
        ["match_type", "match_label", "has_los_link", "has_symitar_link"],
    ),
    (
        ["performance", "loan status", "charged off", "paid off",
         "snapshot", "monthly balance"],
        ["fct_loan_performance", "dim_loan"],
        [],
        ["loan_status", "status", "snapshot_date"],
    ),
]


@dataclass
class SelectedContext:
    relevant_tables: list[Table] = field(default_factory=list)
    relevant_metrics: list[Metric] = field(default_factory=list)
    relevant_columns: list[Column] = field(default_factory=list)
    relevant_examples: list[Example] = field(default_factory=list)


def _dedup_columns(tables: list[Table]) -> list[Column]:
    seen: dict[str, Column] = {}
    for t in tables:
        for c in t.columns:
            if c.name not in seen:
                seen[c.name] = c
    return list(seen.values())


class ContextSelector:
    """Keyword-based routing that maps a question to relevant context subsets."""

    def __init__(self, ctx: AllContext) -> None:
        self._ctx = ctx
        self._table_idx: dict[str, Table] = {t.name: t for t in ctx.tables}
        self._metric_idx: dict[str, Metric] = {m.name: m for m in ctx.metrics}

    def _matched_routes(self, question: str) -> list[_Route]:
        q = question.lower()
        return [r for r in _ROUTES if any(kw in q for kw in r[0])]

    def _collect_names(
        self, routes: list[_Route]
    ) -> tuple[set[str], set[str]]:
        tables: set[str] = set()
        metrics: set[str] = set()
        for _, t, m, _ in routes:
            tables.update(t)
            metrics.update(m)
        return tables, metrics

    def _select_examples(self, metric_names: set[str]) -> list[Example]:
        if not metric_names:
            return []
        return [
            e for e in self._ctx.examples
            if any(n.replace("_", " ") in e.question.lower() for n in metric_names)
        ]

    def select(self, question: str) -> SelectedContext:
        """Return the allowlisted context subset relevant to this question."""
        routes = self._matched_routes(question)
        if not routes:
            return SelectedContext()

        table_names, metric_names = self._collect_names(routes)
        tables = [self._table_idx[n] for n in table_names if n in self._table_idx]
        metrics = [
            self._metric_idx[n] for n in metric_names if n in self._metric_idx
        ]
        return SelectedContext(
            relevant_tables=tables,
            relevant_metrics=metrics,
            relevant_columns=_dedup_columns(tables),
            relevant_examples=self._select_examples(metric_names),
        )
