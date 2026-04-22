from pathlib import Path

import yaml
from pydantic import BaseModel, Field

_PROFILES_DIR = Path(__file__).parents[2] / "profiles"


class SynthProfile(BaseModel):
    seed: int = 42
    applications: int = Field(gt=0)
    approval_rate: float = Field(ge=0.0, le=1.0)
    funding_rate: float = Field(ge=0.0, le=1.0)


def load_profile(name: str) -> SynthProfile:
    path = _PROFILES_DIR / f"{name}.yaml"
    with path.open() as fh:
        data = yaml.safe_load(fh)
    return SynthProfile(**data)
