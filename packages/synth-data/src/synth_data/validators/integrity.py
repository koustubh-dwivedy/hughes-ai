from dataclasses import dataclass
from datetime import datetime

from synth_data.generators.origence import OrigenceData
from synth_data.generators.symitar_types import SymitarData
from synth_data.reconciliation import ReconciliationRow


@dataclass
class ValidationResult:
    check_name: str
    passed: bool
    detail: str


def _check_fk_integrity(
    origence: OrigenceData, symitar: SymitarData
) -> ValidationResult:
    funded_ids = {fe.application_id for fe in origence.funding_events}
    violations = [
        loan.loan_id
        for loan in symitar.booked_loans
        if loan.application_id is not None and loan.application_id not in funded_ids
    ]
    if violations:
        return ValidationResult(
            check_name="fk_integrity",
            passed=False,
            detail=f"{len(violations)} booked_loans reference non-existent funding events",  # noqa: E501  # long but clear
        )
    return ValidationResult(
        check_name="fk_integrity",
        passed=True,
        detail="all booked_loan.application_id values exist in funding_events",
    )


def _check_temporal_ordering(
    origence: OrigenceData, symitar: SymitarData
) -> ValidationResult:
    funded_at: dict[str, datetime] = {
        fe.application_id: fe.funded_at for fe in origence.funding_events
    }
    violations = [
        loan.loan_id
        for loan in symitar.booked_loans
        if (
            loan.application_id is not None
            and loan.application_id in funded_at
            and loan.originated_at < funded_at[loan.application_id]
        )
    ]
    if violations:
        return ValidationResult(
            check_name="temporal_ordering",
            passed=False,
            detail=f"{len(violations)} loans have originated_at < funded_at",
        )
    return ValidationResult(
        check_name="temporal_ordering",
        passed=True,
        detail="all originated_at >= funded_at",
    )


def _check_plausibility(origence: OrigenceData) -> ValidationResult:
    n_apps = len(origence.applications)
    n_funded = len(origence.funding_events)
    if n_apps == 0:
        return ValidationResult(
            check_name="plausibility",
            passed=False,
            detail="no applications generated",
        )
    ratio = n_funded / n_apps
    if not 0.05 <= ratio <= 0.95:
        return ValidationResult(
            check_name="plausibility",
            passed=False,
            detail=f"funding ratio {ratio:.2%} outside expected range [5%, 95%]",
        )
    return ValidationResult(
        check_name="plausibility",
        passed=True,
        detail=f"funding ratio {ratio:.2%} within expected range",
    )


def validate_integrity(
    origence: OrigenceData,
    symitar: SymitarData,
    rows: list[ReconciliationRow],
) -> list[ValidationResult]:
    return [
        _check_fk_integrity(origence, symitar),
        _check_temporal_ordering(origence, symitar),
        _check_plausibility(origence),
    ]
