"""Pydantic models for the officer-branch dashboard panel."""

from pydantic import BaseModel


class TopBorrower(BaseModel):
    member_name: str
    balance: float
    share_pct: float


class LoanMixItem(BaseModel):
    product: str
    balance: float
    share_pct: float


class WaterfallStep(BaseModel):
    product: str
    delta: float


class SingleLoanCount(BaseModel):
    product: str
    count: int


class ComboBalanceRate(BaseModel):
    product: str
    balance: float
    weighted_avg_rate: float


class OfficerBranchData(BaseModel):
    total_loans: float
    account_count: int
    avg_loan_balance: float
    top_25_borrowers: list[TopBorrower]
    loan_mix_donut: list[LoanMixItem]
    change_by_type_waterfall: list[WaterfallStep]
    single_loan_customers_by_type: list[SingleLoanCount]
    combo_balance_rate: list[ComboBalanceRate]
