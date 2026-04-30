import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

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
class DepositBalanceRow:
    balance_id: str
    account_id: str
    snapshot_date: date
    balance: float


@dataclass
class DepositEventRow:
    event_id: str
    account_id: str
    event_type: str
    event_at: datetime
    amount: float


@dataclass
class DepositData:
    products: list[DepositProductRow]
    accounts: list[DepositAccountRow]
    balances: list[DepositBalanceRow] = field(default_factory=list)
    events: list[DepositEventRow] = field(default_factory=list)


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


def _generate_balance_history(
    accounts: list[DepositAccountRow],
    seed: int,
) -> tuple[list[DepositBalanceRow], list[DepositEventRow]]:
    rng = np.random.default_rng(seed + 50)
    bals: list[DepositBalanceRow] = []
    evts: list[DepositEventRow] = []
    for acc in accounts:
        o = acc.opened_at.date().replace(day=1)
        end_dt = acc.closed_at.date() if acc.closed_at else _REF_DATE.date()
        e = end_dt.replace(day=1)
        n = (e.year - o.year) * 12 + (e.month - o.month) + 1
        if n < 1:
            continue
        fin = float(acc.current_balance)
        ini = fin if n == 1 else max(
            1.0, round(float(rng.uniform(0.7 * fin, 1.3 * fin)), 2))
        walk = np.linspace(ini, fin, n) + rng.normal(0, max(1.0, fin * 0.05), n)
        walk[0], walk[-1] = ini, fin
        walk = np.round(np.maximum(0.01, walk), 2).astype(np.float64)
        ids = [str(uuid.UUID(bytes=bytes(r)))
               for r in rng.integers(0, 256, (2 * n + 2, 16), dtype=np.uint8)]
        k = 0
        evts.append(DepositEventRow(event_id=ids[k], account_id=acc.account_id,
            event_type="opened", event_at=acc.opened_at, amount=round(ini, 2)))
        k += 1
        prev_sum = 0.0
        for i in range(n):
            mo = o.month - 1 + i
            snap = date(o.year + mo // 12, mo % 12 + 1, 1)
            bals.append(DepositBalanceRow(balance_id=ids[k], account_id=acc.account_id,
                snapshot_date=snap, balance=float(walk[i])))
            k += 1
            if i > 0:
                raw_d = float(walk[i]) - float(walk[i - 1])
                d_last = round(fin - ini - prev_sum, 2)
                delta = d_last if i == n - 1 else round(raw_d, 2)
                prev_sum += delta
                evts.append(DepositEventRow(event_id=ids[k], account_id=acc.account_id,
                    event_type="balance_change",
                    event_at=acc.opened_at + timedelta(days=i * 30),
                    amount=delta))
                k += 1
        if acc.closed_at:
            evts.append(DepositEventRow(event_id=ids[k], account_id=acc.account_id,
                event_type="closed", event_at=acc.closed_at, amount=round(fin, 2)))
    return bals, evts


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

    bals, evts = _generate_balance_history(accounts, profile.seed)
    return DepositData(products=products, accounts=accounts, balances=bals, events=evts)
