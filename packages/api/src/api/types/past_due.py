"""Pydantic models for the past-due dashboard panel."""

from datetime import date

from pydantic import BaseModel


class OfficerDelinquency(BaseModel):
    officer_name: str
    balance: float
    count: int


class DelinquencyTrendMonth(BaseModel):
    month: date
    bucket_30_59: float
    bucket_60_89: float
    bucket_90_plus: float


class PastDueRatioPoint(BaseModel):
    month: date
    ratio: float


class PastDueData(BaseModel):
    past_due_total: float
    past_due_total_delta: float
    nonaccrual_total: float
    nonaccrual_total_delta: float
    watchlist_count: int
    watchlist_count_delta: int
    nonperforming_balance: float
    nonperforming_balance_delta: float
    past_due_by_officer: list[OfficerDelinquency]
    delinquency_trend_13_months: list[DelinquencyTrendMonth]
    past_due_ratio_trend: list[PastDueRatioPoint]
