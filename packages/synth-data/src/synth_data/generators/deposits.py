import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import numpy as np

from synth_data.config import SynthProfile
from synth_data.generators.members import MemberRow

_REF_DATE = datetime(2026, 4, 1, tzinfo=UTC)

_PRODUCTS = [
    ("Demand", True),
    ("Interest Bearing", False),
    ("Money Market", True),
    ("Savings", True),
    ("Time Deposits", False),
]

_BALANCE_RANGES: dict[str, tuple[float, float]] = {
    "Demand": (100.0, 5_000.0),
    "Savings": (200.0, 20_000.0),
    "Money Market": (5_000.0, 100_000.0),
    "Interest Bearing": (1_000.0, 50_000.0),
    "Time Deposits": (5_000.0, 150_000.0),
}


@dataclass
class DepositProductRow:
    product_id: str
    name: str
    is_core_deposit: bool


@dataclass
class DepositAccountRow:
    account_id: str
    member_id: str
    branch_name: str
    product_id: str
    opened_at: datetime
    closed_at: datetime | None
    current_balance: float


@dataclass
class DepositData:
    products: list[DepositProductRow]
    accounts: list[DepositAccountRow]


def _gen_products(seed: int) -> list[DepositProductRow]:
    rng = np.random.default_rng(seed + 40)
    products = []
    for name, is_core in _PRODUCTS:
        raw = rng.integers(0, 256, 16, dtype=np.uint8)
        products.append(DepositProductRow(
            product_id=str(uuid.UUID(bytes=bytes(raw))),
            name=name,
            is_core_deposit=is_core,
        ))
    return products


def generate_deposits(
    profile: SynthProfile,
    members: list[MemberRow],
    branch_names: list[str],
) -> DepositData:
    products = _gen_products(profile.seed)
    n = profile.deposit_account_count
    rng = np.random.default_rng(profile.seed + 40)

    core_prods = [p for p in products if p.is_core_deposit]
    noncr_prods = [p for p in products if not p.is_core_deposit]

    raw_ids = rng.integers(0, 256, size=(n, 16), dtype=np.uint8)
    account_ids = [str(uuid.UUID(bytes=bytes(raw_ids[i]))) for i in range(n)]

    is_core_flags = rng.random(n) < 0.60
    core_picks = rng.integers(0, len(core_prods), n)
    noncr_picks = rng.integers(0, len(noncr_prods), n)
    member_picks = rng.integers(0, len(members), n)
    branch_picks = rng.integers(0, len(branch_names), n)
    days_open = rng.integers(365, 365 * 6, n)
    is_closed = rng.random(n) < 0.10
    days_since_close = rng.integers(1, 730, n)

    accounts: list[DepositAccountRow] = []
    for i in range(n):
        prod = core_prods[int(core_picks[i])] if is_core_flags[i] \
            else noncr_prods[int(noncr_picks[i])]
        lo, hi = _BALANCE_RANGES[prod.name]
        balance = round(float(rng.uniform(lo, hi)), 2)
        opened = _REF_DATE - timedelta(days=int(days_open[i]))
        closed: datetime | None = None
        if is_closed[i]:
            closed = opened + timedelta(days=int(days_since_close[i]))
            if closed > _REF_DATE:
                closed = _REF_DATE
        accounts.append(DepositAccountRow(
            account_id=account_ids[i],
            member_id=members[int(member_picks[i])].member_id,
            branch_name=branch_names[int(branch_picks[i])],
            product_id=prod.product_id,
            opened_at=opened,
            closed_at=closed,
            current_balance=balance,
        ))

    return DepositData(products=products, accounts=accounts)
