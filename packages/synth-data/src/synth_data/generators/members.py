import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import numpy as np
from faker import Faker

from synth_data.config import SynthProfile

_REF_DATE = datetime(2026, 4, 1, tzinfo=UTC)


@dataclass
class MemberRow:
    member_id: str
    first_name: str
    last_name: str
    joined_at: datetime
    home_branch_name: str


def _gen_member_uuids(rng: np.random.Generator, n: int) -> list[str]:
    raw = rng.integers(0, 256, size=(n, 16), dtype=np.uint8)
    return [str(uuid.UUID(bytes=bytes(row))) for row in raw]


def _gen_names(seed: int, n: int) -> list[tuple[str, str]]:
    Faker.seed(seed)
    fake = Faker()
    return [(fake.first_name(), fake.last_name()) for _ in range(n)]


def _gen_joined_at(rng: np.random.Generator, n: int) -> list[datetime]:
    days_ago = rng.integers(365, 365 * 6, n)
    return [_REF_DATE - timedelta(days=int(d)) for d in days_ago]


def generate_members(
    profile: SynthProfile, branch_names: list[str]
) -> list[MemberRow]:
    n = profile.member_count
    rng = np.random.default_rng(profile.seed + 10)
    member_uuids = _gen_member_uuids(rng, n)
    names = _gen_names(profile.seed + 10, n)
    joined_dates = _gen_joined_at(rng, n)
    branch_idxs = rng.integers(0, len(branch_names), n)
    return [
        MemberRow(
            member_id=member_uuids[i],
            first_name=names[i][0],
            last_name=names[i][1],
            joined_at=joined_dates[i],
            home_branch_name=branch_names[int(branch_idxs[i])],
        )
        for i in range(n)
    ]


def assign_member_id(loan_id: str, members: list[MemberRow]) -> str:
    h = int(hashlib.sha256(loan_id.encode()).hexdigest(), 16)
    return members[h % len(members)].member_id
