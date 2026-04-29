import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import numpy as np
from faker import Faker

from synth_data.config import SynthProfile
from synth_data.generators.symitar_types import OfficerRow

_REF_DATE = datetime(2026, 4, 1, tzinfo=UTC)


def _gen_officer_uuids(rng: np.random.Generator, n: int) -> list[str]:
    raw = rng.integers(0, 256, size=(n, 16), dtype=np.uint8)
    return [str(uuid.UUID(bytes=bytes(row))) for row in raw]


def _gen_officer_names(seed: int, n: int) -> list[str]:
    Faker.seed(seed)
    fake = Faker()
    return [fake.name() for _ in range(n)]


def _gen_hired_at(rng: np.random.Generator, n: int) -> list[datetime]:
    days_ago = rng.integers(365 * 2, 365 * 8, n)
    return [_REF_DATE - timedelta(days=int(d)) for d in days_ago]


def _departed_indices(officer_count: int, branch_count: int) -> set[int]:
    officers_per_branch = officer_count // branch_count
    if officers_per_branch < 4:
        return set()
    last_in_branch_0 = (officers_per_branch - 1) * branch_count
    last_in_branch_1 = (officers_per_branch - 1) * branch_count + 1
    return {last_in_branch_0, last_in_branch_1}


def generate_officers(
    profile: SynthProfile, branch_names: list[str]
) -> list[OfficerRow]:
    n = profile.officer_count
    rng = np.random.default_rng(profile.seed + 20)
    officer_uuids = _gen_officer_uuids(rng, n)
    names = _gen_officer_names(profile.seed + 20, n)
    hired_dates = _gen_hired_at(rng, n)
    departed = _departed_indices(n, len(branch_names))
    return [
        OfficerRow(
            officer_id=officer_uuids[i],
            name=names[i],
            branch_name=branch_names[i % len(branch_names)],
            hired_at=hired_dates[i],
            status="departed" if i in departed else "active",
        )
        for i in range(n)
    ]


def assign_officer_id(
    loan_id: str,
    branch_name: str,
    officers: list[OfficerRow],
) -> str:
    candidates = [o for o in officers if o.branch_name == branch_name]
    h = int(hashlib.sha256(loan_id.encode()).hexdigest(), 16)
    return candidates[h % len(candidates)].officer_id
