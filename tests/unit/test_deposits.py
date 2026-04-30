import pytest

from synth_data.config import SynthProfile
from synth_data.generators.deposits import DepositData, generate_deposits
from synth_data.generators.members import MemberRow
from datetime import datetime, timezone


_REF_DATE = datetime(2025, 1, 1, tzinfo=timezone.utc)

_PROFILE = SynthProfile(
    seed=42,
    applications=50,
    approval_rate=0.72,
    funding_rate=0.85,
    member_count=200,
    deposit_account_count=400,
)
_BRANCH_NAMES = ["Alpha", "Bravo", "Charlie", "Delta", "Echo"]


def _members() -> list[MemberRow]:
    return [
        MemberRow(
            member_id=f"mem-{i:04d}",
            first_name="A",
            last_name="B",
            joined_at=_REF_DATE,
            home_branch_name=_BRANCH_NAMES[i % len(_BRANCH_NAMES)],
        )
        for i in range(_PROFILE.member_count)
    ]


@pytest.fixture(scope="module")
def deposits() -> DepositData:
    return generate_deposits(_PROFILE, _members(), _BRANCH_NAMES)


def test_exactly_five_products(deposits: DepositData) -> None:
    assert len(deposits.products) == 5
    assert {p.name for p in deposits.products} == {
        "Demand", "Interest Bearing", "Money Market", "Savings", "Time Deposits"
    }


def test_account_count(deposits: DepositData) -> None:
    assert 7840 <= len(deposits.accounts) <= 8160 or len(deposits.accounts) == 400
    # profile sets 400 for this test; just assert within 2% of configured count
    n = _PROFILE.deposit_account_count
    assert abs(len(deposits.accounts) - n) / n <= 0.02


def test_all_fks_resolve(deposits: DepositData) -> None:
    member_ids = {f"mem-{i:04d}" for i in range(_PROFILE.member_count)}
    branch_names = set(_BRANCH_NAMES)
    product_ids = {p.product_id for p in deposits.products}
    for a in deposits.accounts:
        assert a.member_id in member_ids
        assert a.branch_name in branch_names
        assert a.product_id in product_ids


def test_core_noncr_mix(deposits: DepositData) -> None:
    core_ids = {p.product_id for p in deposits.products if p.is_core_deposit}
    core_n = sum(1 for a in deposits.accounts if a.product_id in core_ids)
    ratio = core_n / len(deposits.accounts)
    assert 0.55 <= ratio <= 0.65


def test_per_branch_coverage(deposits: DepositData) -> None:
    seen = {a.branch_name for a in deposits.accounts}
    assert seen == set(_BRANCH_NAMES)


def test_deterministic() -> None:
    m = _members()
    d1 = generate_deposits(_PROFILE, m, _BRANCH_NAMES)
    d2 = generate_deposits(_PROFILE, m, _BRANCH_NAMES)
    assert [a.account_id for a in d1.accounts] == [a.account_id for a in d2.accounts]
