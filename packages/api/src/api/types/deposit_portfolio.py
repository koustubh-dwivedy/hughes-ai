"""Pydantic models for the deposit-portfolio dashboard panel."""

from pydantic import BaseModel


class TopDeposit(BaseModel):
    member_name: str
    balance: float
    share_pct: float


class BranchBalance(BaseModel):
    branch_name: str
    balance: float


class ProductBalance(BaseModel):
    product: str
    balance: float
    share_pct: float


class ProductDelta(BaseModel):
    product: str
    delta: float


class AccountActivity(BaseModel):
    count: int
    amount: float


class NewVsClosed(BaseModel):
    opened: AccountActivity
    closed: AccountActivity


class DepositPortfolioData(BaseModel):
    total_deposits: float
    mtd_change: float
    ytd_change: float
    avg_balance_per_customer: float
    account_count: int
    top_25_deposits: list[TopDeposit]
    deposits_by_branch: list[BranchBalance]
    deposit_mix: list[ProductBalance]
    change_by_product: list[ProductDelta]
    new_vs_closed_accounts: NewVsClosed
