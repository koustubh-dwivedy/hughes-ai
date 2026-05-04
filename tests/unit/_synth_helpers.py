"""Module-scoped helpers so existing tests keep their concise call style
after the HUG-162 generator-signature change."""

from synth_data.config import SynthProfile, load_product_catalog
from synth_data.generators.members import MemberRow, generate_members
from synth_data.generators.origence import OrigenceData, generate_origence_data
from synth_data.generators.symitar import SymitarData, generate_symitar_data

DEFAULT_BRANCHES = [
    "Main Branch", "North Branch", "South Branch", "East Branch", "West Branch",
]

_CATALOG = load_product_catalog()
_MEMBERS_CACHE: dict[int, list[MemberRow]] = {}


def members_for(profile: SynthProfile) -> list[MemberRow]:
    key = (profile.seed, profile.member_count)[0]
    if key not in _MEMBERS_CACHE:
        _MEMBERS_CACHE[key] = generate_members(profile, DEFAULT_BRANCHES)
    return _MEMBERS_CACHE[key]


def origence_for(profile: SynthProfile) -> OrigenceData:
    return generate_origence_data(profile, _CATALOG, members_for(profile))


def symitar_for(profile: SynthProfile, origence: OrigenceData) -> SymitarData:
    return generate_symitar_data(origence, profile, _CATALOG)
