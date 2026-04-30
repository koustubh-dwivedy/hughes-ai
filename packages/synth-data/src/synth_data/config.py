from pathlib import Path

import yaml
from pydantic import BaseModel, Field

_PROFILES_DIR = Path(__file__).parents[2] / "profiles"


class SynthProfile(BaseModel):
    seed: int = 42
    applications: int = Field(gt=0)
    approval_rate: float = Field(ge=0.0, le=1.0)
    funding_rate: float = Field(ge=0.0, le=1.0)
    dpd_30_rate: float = Field(default=0.08, ge=0.0, le=1.0)
    charge_off_rate: float = Field(default=0.02, ge=0.0, le=1.0)
    branch_count: int = Field(default=5, gt=0)
    standalone_loan_count: int = Field(default=10, gt=0)
    member_count: int = Field(default=3000, gt=0)
    officer_count: int = Field(default=20, gt=0)
    deposit_account_count: int = Field(default=8000, gt=0)
    history_months: int = Field(default=26, gt=0)


def load_profile(name: str) -> SynthProfile:
    path = _PROFILES_DIR / f"{name}.yaml"
    with path.open() as fh:
        data = yaml.safe_load(fh)
    return SynthProfile(**data)
