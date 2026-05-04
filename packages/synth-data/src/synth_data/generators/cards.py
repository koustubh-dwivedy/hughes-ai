"""Credit-card transaction ledger generator.

Generates monthly card_balances snapshots and card_transactions for every
booked loan whose product_type_name == 'credit_card'. Balance movement
each month closes: balance(t) = balance(t-1) + Σ purchases + Σ fees
+ Σ interest_accrual − Σ payments (to within $0.01).
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import numpy as np

from synth_data.config import SynthProfile
from synth_data.generators.symitar_types import BookedLoanRow

_REF_DATE = datetime(2026, 4, 1, tzinfo=UTC)
_MERCHANT_CATEGORIES = [
    "grocery", "gas", "restaurant", "retail", "online_marketplace",
    "utilities", "travel", "entertainment", "healthcare", "subscription",
]


@dataclass
class CardBalanceRow:
    balance_id: str
    loan_id: str
    snapshot_date: date
    balance: Decimal
    credit_limit: Decimal


@dataclass
class CardTransactionRow:
    transaction_id: str
    loan_id: str
    occurred_at: datetime
    amount: Decimal
    txn_type: str
    merchant_category: str | None


@dataclass
class CardData:
    balances: list[CardBalanceRow]
    transactions: list[CardTransactionRow]


def _new_uuid(rng: np.random.Generator) -> str:
    return str(uuid.UUID(bytes=bytes(rng.integers(0, 256, 16, dtype=np.uint8))))


def _snapshot_date(originated_at: datetime, month_offset: int) -> date:
    y = originated_at.year + (originated_at.month - 1 + month_offset) // 12
    m = (originated_at.month - 1 + month_offset) % 12 + 1
    return date(y, m, 1)


def _months_active(originated_at: datetime) -> int:
    return max(
        0,
        (_REF_DATE.year - originated_at.year) * 12
        + (_REF_DATE.month - originated_at.month),
    )


def _accrue_interest(
    rng: np.random.Generator, loan_id: str, month_start: datetime,
    starting_balance: float, apr: float,
) -> tuple[float, CardTransactionRow | None]:
    if starting_balance <= 0:
        return 0.0, None
    interest = round(starting_balance * apr / 12.0, 2)
    if interest < 0.01:
        return 0.0, None
    txn = CardTransactionRow(
        _new_uuid(rng), loan_id, month_start + timedelta(days=1),
        Decimal(str(interest)), "interest_accrual", None,
    )
    return interest, txn


def _gen_purchases(
    rng: np.random.Generator, loan_id: str, month_start: datetime,
    credit_limit: float, current_balance: float, txns_per_month: int,
) -> tuple[float, list[CardTransactionRow]]:
    txns: list[CardTransactionRow] = []
    balance = current_balance
    for _ in range(txns_per_month):
        amt = float(rng.uniform(8.0, 250.0))
        amt = min(amt, max(0.0, credit_limit - balance))
        if amt < 1.0:
            continue
        day = int(rng.integers(1, 28))
        txns.append(CardTransactionRow(
            _new_uuid(rng), loan_id, month_start + timedelta(days=day),
            Decimal(str(round(amt, 2))), "purchase",
            _MERCHANT_CATEGORIES[int(rng.integers(0, len(_MERCHANT_CATEGORIES)))],
        ))
        balance += amt
    return balance, txns


def _gen_payment(
    rng: np.random.Generator, loan_id: str, month_start: datetime, balance: float,
) -> tuple[float, CardTransactionRow | None]:
    if balance <= 0:
        return balance, None
    pay_frac = (
        float(rng.uniform(0.05, 0.15)) if rng.random() < 0.7
        else float(rng.uniform(0.50, 1.00))
    )
    payment = round(balance * pay_frac, 2)
    if payment < 1.0:
        return balance, None
    txn = CardTransactionRow(
        _new_uuid(rng), loan_id,
        month_start + timedelta(days=int(rng.integers(20, 28))),
        Decimal(str(-payment)), "payment", None,
    )
    return balance - payment, txn


def _gen_month(
    rng: np.random.Generator,
    loan_id: str,
    month_start: datetime,
    credit_limit: float,
    starting_balance: float,
    txns_per_month: int,
    apr: float,
) -> tuple[float, list[CardTransactionRow]]:
    """Simulate one month of card activity. Returns ending balance + transactions."""
    txns: list[CardTransactionRow] = []
    interest_amt, int_txn = _accrue_interest(
        rng, loan_id, month_start, starting_balance, apr,
    )
    balance = starting_balance + interest_amt
    if int_txn is not None:
        txns.append(int_txn)
    balance, purchase_txns = _gen_purchases(
        rng, loan_id, month_start, credit_limit, balance, txns_per_month,
    )
    txns.extend(purchase_txns)
    balance, pay_txn = _gen_payment(rng, loan_id, month_start, balance)
    if pay_txn is not None:
        txns.append(pay_txn)
    if rng.random() < 0.03:
        fee = 35.0
        txns.append(CardTransactionRow(
            _new_uuid(rng), loan_id,
            month_start + timedelta(days=int(rng.integers(15, 28))),
            Decimal(str(fee)), "fee", None,
        ))
        balance += fee
    return max(0.0, round(balance, 2)), txns


def generate_card_data(
    profile: SynthProfile,
    booked_loans: list[BookedLoanRow],
) -> CardData:
    rng = np.random.default_rng(profile.seed + 80)
    cards = [loan for loan in booked_loans if loan.product_type_name == "credit_card"]
    txns_per_month = profile.cards.transactions_per_card_per_month
    balances: list[CardBalanceRow] = []
    transactions: list[CardTransactionRow] = []

    for loan in cards:
        # For credit cards, original_balance is the credit limit.
        credit_limit = float(loan.original_balance)
        apr = float(loan.rate)
        months_active = _months_active(loan.originated_at)
        if months_active == 0:
            continue
        # Initial balance starts modest (0–25% of limit)
        running_bal = float(rng.uniform(0.0, credit_limit * 0.25))

        for mo in range(1, months_active + 1):
            snap = _snapshot_date(loan.originated_at, mo)
            month_start = datetime(snap.year, snap.month, 1, tzinfo=UTC)
            running_bal, month_txns = _gen_month(
                rng, loan.loan_id, month_start, credit_limit, running_bal,
                txns_per_month, apr,
            )
            transactions.extend(month_txns)
            balances.append(CardBalanceRow(
                balance_id=_new_uuid(rng),
                loan_id=loan.loan_id,
                snapshot_date=snap,
                balance=Decimal(str(round(running_bal, 2))),
                credit_limit=Decimal(str(round(credit_limit, 2))),
            ))

    return CardData(balances=balances, transactions=transactions)
