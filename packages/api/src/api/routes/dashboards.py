"""Dashboard router — D1-D4 add their endpoints here."""

import uuid
from datetime import date, datetime

from fastapi import APIRouter

from api.types.dashboard_envelope import DashboardEnvelope

router = APIRouter(prefix="/api/dashboards")


def build_envelope(
    data: object,
    as_of_date: date,
    audit_id: uuid.UUID,
) -> DashboardEnvelope:  # type: ignore[type-arg]
    """Wrap mart data in the standard dashboard response envelope."""
    return DashboardEnvelope(
        data=data,
        as_of_date=as_of_date,
        generated_at=datetime.utcnow(),
        audit_id=audit_id,
    )
