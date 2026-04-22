from dataclasses import dataclass

from synth_data.generators.origence import OrigenceData
from synth_data.generators.symitar_types import SymitarData


@dataclass
class ReconciliationRow:
    application_id: str | None
    loan_id: str
    match_type: str  # matched | unmatched | ambiguous


def reconcile(origence: OrigenceData, symitar: SymitarData) -> list[ReconciliationRow]:
    """Match Symitar booked loans to Origence funding events.

    matched   — booked_loan.application_id links directly to a funding event
    ambiguous — standalone loan whose member_id appears in a funded application
    unmatched — standalone loan with no plausible Origence counterpart
    """
    funded_ids = {fe.application_id for fe in origence.funding_events}
    funded_by_member: dict[str, str] = {
        a.member_id: a.application_id
        for a in origence.applications
        if a.status == "funded"
    }

    rows: list[ReconciliationRow] = []
    for loan in symitar.booked_loans:
        if loan.application_id is not None and loan.application_id in funded_ids:
            rows.append(ReconciliationRow(
                application_id=loan.application_id,
                loan_id=loan.loan_id,
                match_type="matched",
            ))
        elif loan.application_id is None and loan.member_id in funded_by_member:
            rows.append(ReconciliationRow(
                application_id=funded_by_member[loan.member_id],
                loan_id=loan.loan_id,
                match_type="ambiguous",
            ))
        else:
            rows.append(ReconciliationRow(
                application_id=None,
                loan_id=loan.loan_id,
                match_type="unmatched",
            ))
    return rows
