from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, model_validator

_PROFILES_DIR = Path(__file__).parents[2] / "profiles"


class LoanProductSpec(BaseModel):
    code: str
    label: str
    mix: float = Field(ge=0.0, le=1.0)
    rate_range: tuple[float, float]
    term_months: list[int]
    amount_range: tuple[int, int]
    ncua_5300_line_code: str
    cecl_segment: str
    requires_dealer: bool = False
    is_revolving: bool = False


class ShareProductSpec(BaseModel):
    code: str
    label: str
    is_core: bool
    ncua_5300_line_code: str


class CeclSegmentSpec(BaseModel):
    code: str
    label: str
    expected_loss_rate_current: float
    loss_rate_30_59: float
    loss_rate_60_89: float
    loss_rate_90_plus: float


class ProductCatalog(BaseModel):
    loan_products: list[LoanProductSpec]
    share_products: list[ShareProductSpec]
    cecl_segments: list[CeclSegmentSpec]

    @model_validator(mode="after")
    def _check_loan_mix_sums_to_one(self) -> "ProductCatalog":
        total = sum(p.mix for p in self.loan_products)
        if abs(total - 1.0) > 0.001:
            raise ValueError(
                f"loan_products mix percentages must sum to 1.0 (got {total:.4f})"
            )
        return self


class HouseholdProfile(BaseModel):
    paired_share: float = Field(default=0.60, ge=0.0, le=1.0)
    triple_share: float = Field(default=0.10, ge=0.0, le=1.0)
    joint_deposit_share: float = Field(default=0.40, ge=0.0, le=1.0)
    joint_mortgage_share: float = Field(default=0.25, ge=0.0, le=1.0)
    pod_beneficiary_share: float = Field(default=0.15, ge=0.0, le=1.0)


class DealerProfile(BaseModel):
    dealer_count: int = Field(default=25, gt=0)
    auto_franchise_share: float = Field(default=0.55, ge=0.0, le=1.0)


class CardProfile(BaseModel):
    transactions_per_card_per_month: int = Field(default=8, ge=0)


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
    watchlist_share: float = Field(default=0.04, ge=0.0, le=1.0)
    households: HouseholdProfile = Field(default_factory=HouseholdProfile)
    dealers: DealerProfile = Field(default_factory=DealerProfile)
    cards: CardProfile = Field(default_factory=CardProfile)


def load_profile(name: str) -> SynthProfile:
    path = _PROFILES_DIR / f"{name}.yaml"
    with path.open() as fh:
        data = yaml.safe_load(fh)
    return SynthProfile(**data)


def load_product_catalog() -> ProductCatalog:
    path = _PROFILES_DIR / "products.yaml"
    with path.open() as fh:
        data: dict[str, Any] = yaml.safe_load(fh)
    return ProductCatalog(**data)
