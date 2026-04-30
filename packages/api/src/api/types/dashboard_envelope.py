"""Standard typed envelope for all dashboard API responses."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel


class DashboardEnvelope[DataT](BaseModel):
    """Wrapper returned by every /api/dashboards/* endpoint."""

    data: DataT
    as_of_date: date
    generated_at: datetime
    audit_id: uuid.UUID
