"""Auto dealer generator for Origence indirect-lending narrative.

~25 dealers, Pareto-weighted (top 5 dealers receive ~60% of indirect bookings).
Used by symitar.py to populate booked_loans.dealer_id on auto_indirect loans.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import numpy as np

from synth_data.config import SynthProfile

_REF_DATE = datetime(2026, 4, 1, tzinfo=UTC)
_DEALER_NAME_BASES = [
    "Maple Auto", "Sunrise Motors", "Crossroads Cars", "Prairie Auto Group",
    "Heritage Motors", "Apex Auto", "Riverside Motors", "Capitol Cars",
    "Gateway Auto", "Summit Motors", "Lakeside Auto", "Bayview Cars",
    "Ridgeline Motors", "Westwind Auto", "Northstar Motors", "Skyline Cars",
    "Highland Auto", "Brookside Motors", "Foothill Auto", "Coastal Cars",
    "Sterling Motors", "Pioneer Auto", "Vanguard Cars", "Liberty Motors",
    "Eagle Auto", "Phoenix Motors", "Atlas Cars", "Granite Auto",
    "Cascade Motors", "Meridian Cars",
]
_CITIES = [
    ("Springfield", "IL"), ("Madison", "WI"), ("Columbus", "OH"),
    ("Lincoln", "NE"), ("Aurora", "CO"), ("Salem", "OR"), ("Boise", "ID"),
    ("Tacoma", "WA"), ("Provo", "UT"), ("Fresno", "CA"),
]
_MARKUP_TIERS = ["standard", "standard", "premium", "aggressive"]  # 50/25/25 weight


@dataclass
class DealerRow:
    dealer_id: str
    name: str
    dealer_type: str
    address_city: str
    address_state: str
    markup_tier: str
    active_from: datetime
    active_until: datetime | None


def generate_dealers(profile: SynthProfile) -> list[DealerRow]:
    rng = np.random.default_rng(profile.seed + 60)
    n = profile.dealers.dealer_count
    if n > len(_DEALER_NAME_BASES):
        raise ValueError(f"dealer_count {n} exceeds available name pool")

    name_idxs = rng.choice(len(_DEALER_NAME_BASES), n, replace=False)
    city_idxs = rng.integers(0, len(_CITIES), n)
    franchise_share = profile.dealers.auto_franchise_share
    is_franchise = rng.random(n) < franchise_share
    tier_idxs = rng.integers(0, len(_MARKUP_TIERS), n)
    days_ago = rng.integers(365, 365 * 8, n)

    dealers = []
    for i in range(n):
        city, state = _CITIES[int(city_idxs[i])]
        d_uuid = uuid.UUID(bytes=bytes(rng.integers(0, 256, 16, dtype=np.uint8)))
        dealers.append(DealerRow(
            dealer_id=str(d_uuid),
            name=_DEALER_NAME_BASES[int(name_idxs[i])],
            dealer_type="auto_franchise" if is_franchise[i] else "auto_independent",
            address_city=city,
            address_state=state,
            markup_tier=_MARKUP_TIERS[int(tier_idxs[i])],
            active_from=_REF_DATE - timedelta(days=int(days_ago[i])),
            active_until=None,
        ))
    return dealers


def assign_dealer_id(
    rng: np.random.Generator,
    dealers: list[DealerRow],
) -> str:
    """Pareto pick: top 5 dealers get ~60% of bookings.

    Implemented with a power-law over the dealer index.
    """
    n = len(dealers)
    weights = 1.0 / (np.arange(1, n + 1) ** 1.4)
    weights /= weights.sum()
    idx = int(rng.choice(n, p=weights))
    return dealers[idx].dealer_id


def dealer_reserve_for(
    rng: np.random.Generator,
    funded_amount: Decimal,
    markup_tier: str,
) -> Decimal:
    """Industry-typical dealer reserve: 1-3% of funded amount, tier-modulated."""
    base = {"standard": 0.015, "premium": 0.020, "aggressive": 0.028}.get(
        markup_tier, 0.015
    )
    jitter = float(rng.uniform(-0.003, 0.003))
    return Decimal(str(round(float(funded_amount) * max(0.005, base + jitter), 2)))
