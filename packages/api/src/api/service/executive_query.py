"""Executive summary service: composer for the executive-summary dashboard."""

from datetime import date

from api.repo import executive as repo_exec
from api.types.executive_summary import (
    ExecutiveSummaryData,
    KpiTrendPoint,
    PastDueAgingBucket,
)


def compose_executive_summary(as_of: date, db_url: str) -> ExecutiveSummaryData:
    """Fetch and assemble all panels for the executive-summary dashboard."""
    kpis = repo_exec.fetch_executive_kpis(as_of, db_url)
    trend = repo_exec.fetch_kpis_trend(as_of, db_url)
    aging = repo_exec.fetch_past_due_aging(as_of, db_url)
    return ExecutiveSummaryData(
        total_loans_balance=float(kpis.get("total_loans_balance") or 0),
        total_deposits_balance=float(kpis.get("total_deposits_balance") or 0),
        loan_to_deposit_ratio=float(kpis.get("loan_to_deposit_ratio") or 0),
        core_deposit_ratio=float(kpis.get("core_deposit_ratio") or 0),
        blended_past_due_ratio=float(kpis.get("blended_past_due_ratio") or 0),
        monthly_loan_growth=float(kpis.get("monthly_loan_growth") or 0),
        monthly_deposit_growth=float(kpis.get("monthly_deposit_growth") or 0),
        ytd_loan_growth=float(kpis.get("ytd_loan_growth") or 0),
        ytd_deposit_growth=float(kpis.get("ytd_deposit_growth") or 0),
        weighted_avg_loan_rate=float(kpis.get("weighted_avg_loan_rate") or 0),
        weighted_avg_deposit_rate=float(kpis.get("weighted_avg_deposit_rate") or 0),
        rate_spread=float(kpis.get("rate_spread") or 0),
        kpi_trend_13_months=[
            KpiTrendPoint(
                month=r["month"],
                total_loans_balance=float(r["total_loans_balance"]),
                total_deposits_balance=float(r["total_deposits_balance"]),
                blended_past_due_ratio=float(r["blended_past_due_ratio"]),
                rate_spread=float(r["rate_spread"]),
            )
            for r in trend
        ],
        past_due_aging=[
            PastDueAgingBucket(
                bucket=str(r["bucket"]),
                balance=float(r["balance"]),
                loan_count=int(r["loan_count"]),
            )
            for r in aging
        ],
    )
