"""Pydantic models for the executive-summary dashboard."""

from datetime import date

from pydantic import BaseModel


class KpiTrendPoint(BaseModel):
    month: date
    total_loans_balance: float
    total_deposits_balance: float
    blended_past_due_ratio: float
    rate_spread: float


class PastDueAgingBucket(BaseModel):
    bucket: str
    balance: float
    loan_count: int


class ExecutiveSummaryData(BaseModel):
    total_loans_balance: float
    total_deposits_balance: float
    loan_to_deposit_ratio: float
    core_deposit_ratio: float
    blended_past_due_ratio: float
    monthly_loan_growth: float
    monthly_deposit_growth: float
    ytd_loan_growth: float
    ytd_deposit_growth: float
    weighted_avg_loan_rate: float
    weighted_avg_deposit_rate: float
    rate_spread: float
    kpi_trend_13_months: list[KpiTrendPoint]
    past_due_aging: list[PastDueAgingBucket]
