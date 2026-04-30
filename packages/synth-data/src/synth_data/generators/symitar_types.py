from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal


@dataclass
class BranchRow:
    branch_name: str
    region: str


@dataclass
class OfficerRow:
    officer_id: str
    name: str
    branch_name: str
    hired_at: datetime
    status: str


@dataclass
class BookedLoanRow:
    loan_id: str
    application_id: str | None
    branch_name: str
    member_id: str
    product_type_name: str
    originated_at: datetime
    original_balance: Decimal
    balance: Decimal
    rate: Decimal
    term_months: int
    maturity_at: datetime
    status: str
    officer_id: str | None = None
    is_nonaccrual: bool = False


@dataclass
class LoanBalanceRow:
    balance_id: str
    loan_id: str
    snapshot_date: date
    balance: Decimal


@dataclass
class PaymentRow:
    payment_id: str
    loan_id: str
    paid_at: datetime
    amount: Decimal
    principal: Decimal
    interest: Decimal
    payment_method: str | None


@dataclass
class DelinquencySnapshotRow:
    snapshot_id: str
    loan_id: str
    snapshot_date: date
    days_past_due: int
    delinquency_bucket: str | None


@dataclass
class LoanLifecycleEventRow:
    event_id: str
    loan_id: str
    event_month: date
    event_type: str


@dataclass
class SymitarData:
    branches: list[BranchRow]
    booked_loans: list[BookedLoanRow]
    loan_balances: list[LoanBalanceRow]
    payments: list[PaymentRow]
    delinquency_snapshots: list[DelinquencySnapshotRow]
    officers: list[OfficerRow] = field(default_factory=list)
    loan_lifecycle_events: list[LoanLifecycleEventRow] = field(default_factory=list)
