from datetime import UTC, datetime

from synth_data.config import SynthProfile
from synth_data.generators.deposits import DepositData, generate_deposits
from synth_data.generators.members import MemberRow

_REF_DATE = datetime(2026, 4, 1, tzinfo=UTC)
_PROFILE = SynthProfile(
    seed=42, applications=50, approval_rate=0.72,
    funding_rate=0.85, member_count=200,
    deposit_account_count=400, history_months=26,
)
_BRANCH_NAMES = ["Alpha", "Bravo", "Charlie", "Delta", "Echo"]


def _members() -> list[MemberRow]:
    return [
        MemberRow(member_id=f"mem-{i:04d}", first_name="A", last_name="B",
                  joined_at=_REF_DATE,
                  home_branch_name=_BRANCH_NAMES[i % len(_BRANCH_NAMES)])
        for i in range(_PROFILE.member_count)
    ]


def _deposits() -> DepositData:
    return generate_deposits(_PROFILE, _members(), _BRANCH_NAMES)


def test_at_least_26_distinct_snapshot_months() -> None:
    d = _deposits()
    months = {r.snapshot_date.replace(day=1) for r in d.balances}
    assert len(months) >= 26, f"only {len(months)} distinct snapshot months"


def test_closed_accounts_no_post_close_snapshots() -> None:
    d = _deposits()
    snap_by_acct: dict[str, list] = {}
    for r in d.balances:
        snap_by_acct.setdefault(r.account_id, []).append(r.snapshot_date)
    for acc in d.accounts:
        if acc.closed_at is None:
            continue
        close_month = acc.closed_at.date().replace(day=1)
        for snap in snap_by_acct.get(acc.account_id, []):
            assert snap <= close_month, (
                f"account {acc.account_id} has snapshot {snap}"
                f" after close {close_month}"
            )


def test_balance_change_reconciles_within_one_cent() -> None:
    d = _deposits()
    opened_bal: dict[str, float] = {}
    delta_sum: dict[str, float] = {}
    for evt in d.events:
        if evt.event_type == "opened":
            opened_bal[evt.account_id] = evt.amount
        elif evt.event_type == "balance_change":
            delta_sum[evt.account_id] = delta_sum.get(evt.account_id, 0.0) + evt.amount
    for acc in d.accounts:
        aid = acc.account_id
        if aid not in opened_bal:
            continue
        expected = round(acc.current_balance - opened_bal[aid], 2)
        actual = round(delta_sum.get(aid, 0.0), 2)
        assert abs(actual - expected) <= 0.01, (
            f"account {aid}: delta_sum={actual}, expected={expected}"
        )


def test_every_account_has_complete_monthly_coverage() -> None:
    from datetime import date
    d = _deposits()
    snaps_by_acct: dict[str, set] = {}
    for r in d.balances:
        snaps_by_acct.setdefault(r.account_id, set()).add(r.snapshot_date)
    ref = date(2026, 4, 1)
    for acc in d.accounts:
        o = acc.opened_at.date().replace(day=1)
        end_dt = acc.closed_at.date() if acc.closed_at else ref
        e = end_dt.replace(day=1)
        n = (e.year - o.year) * 12 + (e.month - o.month) + 1
        if n < 1:
            continue
        snaps = snaps_by_acct.get(acc.account_id, set())
        assert len(snaps) == n, (
            f"account {acc.account_id}: expected {n} snapshots, got {len(snaps)}"
        )
