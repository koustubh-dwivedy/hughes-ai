"""Shared fixtures for unit tests of the synth-data generator pipeline."""

import pytest
from synth_data.config import ProductCatalog, SynthProfile, load_product_catalog
from synth_data.generators.members import MemberRow, generate_members


@pytest.fixture(scope="session")
def profile() -> SynthProfile:
    return SynthProfile(
        seed=42, applications=500, approval_rate=0.72, funding_rate=0.85,
    )


@pytest.fixture(scope="session")
def catalog() -> ProductCatalog:
    return load_product_catalog()


@pytest.fixture(scope="session")
def branch_names() -> list[str]:
    # Mirrors the first N branches generated in symitar.py with the default
    # branch_count of 5.
    return [
        "Main Branch", "North Branch", "South Branch", "East Branch", "West Branch",
    ]


@pytest.fixture(scope="session")
def members(profile: SynthProfile, branch_names: list[str]) -> list[MemberRow]:
    return generate_members(profile, branch_names)
