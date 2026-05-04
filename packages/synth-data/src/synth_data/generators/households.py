"""Household + joint-ownership generator (Member 360 layer).

Builds:
- households                  : one per household with a primary_member_id
- household_members (bridge)  : member -> household with role (primary/joint/dependent)
- account_owners (bridge)     : member -> loan or deposit account with role
                                (primary/joint/pod_beneficiary/authorized_signer)

Heuristics (controlled by profile.households):
- paired_share fraction of members sit in 2-person households (with a partner)
- triple_share fraction sit in 3-person households (partner + 1 dependent)
- Remaining members are 1-person households (singles)
- joint_deposit_share of deposit accounts owned by a paired member also have
  the partner listed as joint owner
- joint_mortgage_share of first_mortgage / heloc / closed_end_2nd loans owned
  by a paired member have the partner as joint owner
- pod_beneficiary_share of single-owner deposit accounts get a POD beneficiary
  drawn from a different household
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np

from synth_data.config import SynthProfile
from synth_data.generators.deposits import DepositAccountRow
from synth_data.generators.members import MemberRow
from synth_data.generators.symitar_types import BookedLoanRow

_REF_DATE = datetime(2026, 4, 1, tzinfo=UTC)

_LOAN_PRODUCTS_JOINT_ELIGIBLE = {"first_mortgage", "heloc", "closed_end_2nd"}


@dataclass
class HouseholdRow:
    household_id: str
    household_name: str
    primary_member_id: str
    formed_at: datetime
    dissolved_at: datetime | None


@dataclass
class HouseholdMemberRow:
    household_member_id: str
    household_id: str
    member_id: str
    role: str
    joined_at: datetime
    left_at: datetime | None


@dataclass
class AccountOwnerRow:
    owner_id: str
    owner_kind: str            # 'loan' | 'deposit'
    owner_account_id: str
    member_id: str
    # primary | joint | pod_beneficiary | authorized_signer
    role: str
    since: datetime
    until_ts: datetime | None


@dataclass
class HouseholdData:
    households: list[HouseholdRow]
    household_members: list[HouseholdMemberRow]
    account_owners: list[AccountOwnerRow]


def _new_uuid(rng: np.random.Generator) -> str:
    raw = rng.integers(0, 256, 16, dtype=np.uint8)
    return str(uuid.UUID(bytes=bytes(raw)))


def _make_paired(
    rng: np.random.Generator, m1: MemberRow, m2: MemberRow,
) -> tuple[HouseholdRow, list[HouseholdMemberRow]]:
    h_id = _new_uuid(rng)
    formed = max(m1.joined_at, m2.joined_at)
    name = f"{m1.last_name} / {m2.last_name}"
    hh = HouseholdRow(h_id, name, m1.member_id, formed, None)
    return hh, [
        HouseholdMemberRow(
            _new_uuid(rng), h_id, m1.member_id, "primary", formed, None,
        ),
        HouseholdMemberRow(
            _new_uuid(rng), h_id, m2.member_id, "joint", formed, None,
        ),
    ]


def _make_triple(
    rng: np.random.Generator, m1: MemberRow, m2: MemberRow, m3: MemberRow,
) -> tuple[HouseholdRow, list[HouseholdMemberRow]]:
    h_id = _new_uuid(rng)
    formed = max(m1.joined_at, m2.joined_at, m3.joined_at)
    name = f"{m1.last_name} / {m2.last_name}"
    hh = HouseholdRow(h_id, name, m1.member_id, formed, None)
    return hh, [
        HouseholdMemberRow(
            _new_uuid(rng), h_id, m1.member_id, "primary", formed, None,
        ),
        HouseholdMemberRow(
            _new_uuid(rng), h_id, m2.member_id, "joint", formed, None,
        ),
        HouseholdMemberRow(
            _new_uuid(rng), h_id, m3.member_id, "dependent", formed, None,
        ),
    ]


def _make_single(
    rng: np.random.Generator, m: MemberRow,
) -> tuple[HouseholdRow, list[HouseholdMemberRow]]:
    h_id = _new_uuid(rng)
    hh = HouseholdRow(h_id, m.last_name, m.member_id, m.joined_at, None)
    return hh, [
        HouseholdMemberRow(
            _new_uuid(rng), h_id, m.member_id, "primary", m.joined_at, None,
        ),
    ]


def _assign_households(
    rng: np.random.Generator,
    members: list[MemberRow],
    profile: SynthProfile,
) -> tuple[list[HouseholdRow], list[HouseholdMemberRow], dict[str, str]]:
    n = len(members)
    indices = list(range(n))
    rng.shuffle(indices)
    paired_target = int(profile.households.paired_share * n)
    triple_target = int(profile.households.triple_share * n)
    paired_target -= paired_target % 2
    households: list[HouseholdRow] = []
    bridges: list[HouseholdMemberRow] = []
    m2h: dict[str, str] = {}
    cursor = 0
    for _ in range(paired_target // 2):
        m1, m2 = members[indices[cursor]], members[indices[cursor + 1]]
        cursor += 2
        hh, br = _make_paired(rng, m1, m2)
        households.append(hh)
        bridges.extend(br)
        m2h[m1.member_id] = hh.household_id
        m2h[m2.member_id] = hh.household_id
    triples = min(triple_target, n - cursor) // 3 * 3
    for _ in range(triples // 3):
        m1, m2, m3 = (members[indices[cursor + k]] for k in range(3))
        cursor += 3
        hh, br = _make_triple(rng, m1, m2, m3)
        households.append(hh)
        bridges.extend(br)
        for m in (m1, m2, m3):
            m2h[m.member_id] = hh.household_id
    for k in range(cursor, n):
        m = members[indices[k]]
        hh, br = _make_single(rng, m)
        households.append(hh)
        bridges.extend(br)
        m2h[m.member_id] = hh.household_id
    return households, bridges, m2h


def _partner_of(
    member_id: str, household_id: str,
    bridges: list[HouseholdMemberRow],
) -> str | None:
    for b in bridges:
        if (b.household_id == household_id
                and b.member_id != member_id
                and b.role in {"primary", "joint"}):
            return b.member_id
    return None


def _build_deposit_owners(
    rng: np.random.Generator,
    deposit_accounts: list[DepositAccountRow],
    member_set: set[str],
    member_ids: list[str],
    maybe_partner: Callable[[str], str | None],
    join_share: float,
    pod_share: float,
) -> list[AccountOwnerRow]:
    owners: list[AccountOwnerRow] = []
    for acc in deposit_accounts:
        if acc.member_id not in member_set:
            continue
        owners.append(AccountOwnerRow(
            _new_uuid(rng), "deposit", acc.account_id, acc.member_id,
            "primary", acc.opened_at, acc.closed_at,
        ))
        partner = maybe_partner(acc.member_id)
        if partner and rng.random() < join_share:
            owners.append(AccountOwnerRow(
                _new_uuid(rng), "deposit", acc.account_id, partner,
                "joint", acc.opened_at, acc.closed_at,
            ))
        elif rng.random() < pod_share:
            other_pool = [m for m in member_ids if m != acc.member_id]
            beneficiary = other_pool[int(rng.integers(0, len(other_pool)))]
            owners.append(AccountOwnerRow(
                _new_uuid(rng), "deposit", acc.account_id, beneficiary,
                "pod_beneficiary", acc.opened_at, acc.closed_at,
            ))
    return owners


def _build_account_owners(
    rng: np.random.Generator,
    members: list[MemberRow],
    deposit_accounts: list[DepositAccountRow],
    booked_loans: list[BookedLoanRow],
    bridges: list[HouseholdMemberRow],
    member_to_household: dict[str, str],
    profile: SynthProfile,
) -> list[AccountOwnerRow]:
    member_ids = [m.member_id for m in members]
    member_set = set(member_ids)

    def _maybe_partner(mid: str) -> str | None:
        h = member_to_household.get(mid)
        if h is None:
            return None
        return _partner_of(mid, h, bridges)

    owners: list[AccountOwnerRow] = _build_deposit_owners(
        rng, deposit_accounts, member_set, member_ids, _maybe_partner,
        profile.households.joint_deposit_share,
        profile.households.pod_beneficiary_share,
    )

    join_mortgage_share = profile.households.joint_mortgage_share
    for loan in booked_loans:
        if loan.member_id not in member_set:
            continue
        owners.append(AccountOwnerRow(
            _new_uuid(rng), "loan", loan.loan_id, loan.member_id,
            "primary", loan.originated_at, None,
        ))
        if loan.product_type_name not in _LOAN_PRODUCTS_JOINT_ELIGIBLE:
            continue
        partner = _maybe_partner(loan.member_id)
        if partner and rng.random() < join_mortgage_share:
            owners.append(AccountOwnerRow(
                _new_uuid(rng), "loan", loan.loan_id, partner,
                "joint", loan.originated_at, None,
            ))
    return owners


def generate_households(
    profile: SynthProfile,
    members: list[MemberRow],
    deposit_accounts: list[DepositAccountRow],
    booked_loans: list[BookedLoanRow],
) -> HouseholdData:
    rng = np.random.default_rng(profile.seed + 70)
    households, bridges, m2h = _assign_households(rng, members, profile)
    owners = _build_account_owners(
        rng, members, deposit_accounts, booked_loans,
        bridges, m2h, profile,
    )
    return HouseholdData(
        households=households,
        household_members=bridges,
        account_owners=owners,
    )
