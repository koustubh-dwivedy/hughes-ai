"""Dashboard router — deposit-portfolio endpoint (D1); D2-D4 add here."""

import time
import uuid
from datetime import date, datetime

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from api.prometheus import (
    dashboard_cache_total,
    dashboard_duration_seconds,
    dashboard_request_total,
)
from api.repo import dashboards as repo_dash
from api.repo import executive as repo_exec
from api.repo import loans as repo_loans
from api.repo.history import save_dashboard_audit
from api.service import dashboard_query, executive_query
from api.types.dashboard_envelope import DashboardEnvelope
from api.types.deposit_portfolio import DepositPortfolioData
from api.types.executive_summary import ExecutiveSummaryData
from api.types.officer_branch import OfficerBranchData
from api.types.past_due import PastDueData

router = APIRouter(prefix="/dashboards")


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


@router.get(
    "/deposit-portfolio",
    response_model=DashboardEnvelope[DepositPortfolioData],
)
async def deposit_portfolio(
    request: Request,
    as_of_date: date | None = Query(default=None),  # noqa: B008
) -> Response:
    rid: str = request.state.request_id
    t0 = time.monotonic()
    db_url: str = request.app.state.db_url
    endpoint = "deposit-portfolio"

    as_of = as_of_date or repo_dash.fetch_latest_deposit_month(db_url)
    as_of_str = str(as_of)

    cached = dashboard_query.cache_get(endpoint, as_of_str)
    if cached is not None:
        dashboard_cache_total.labels(endpoint=endpoint, result="hit").inc()
        return Response(
            content=str(cached),
            media_type="application/json",
            headers={"Cache-Control": "max-age=300, public"},
        )
    dashboard_cache_total.labels(endpoint=endpoint, result="miss").inc()

    data = dashboard_query.compose_deposit_portfolio(as_of, db_url)
    envelope = build_envelope(data, as_of, uuid.UUID(rid))
    json_str = envelope.model_dump_json()

    dashboard_query.cache_set(endpoint, as_of_str, json_str)
    save_dashboard_audit(endpoint, {"as_of": as_of_str}, uuid.UUID(rid), db_url)
    dashboard_request_total.labels(endpoint=endpoint, status="success").inc()
    dashboard_duration_seconds.labels(endpoint=endpoint).observe(time.monotonic() - t0)

    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Cache-Control": "max-age=300, public"},
    )


@router.get(
    "/past-due",
    response_model=DashboardEnvelope[PastDueData],
)
async def past_due(
    request: Request,
    as_of_date: date | None = Query(default=None),  # noqa: B008
) -> Response:
    rid: str = request.state.request_id
    t0 = time.monotonic()
    db_url: str = request.app.state.db_url
    endpoint = "past-due"

    as_of = as_of_date or repo_dash.fetch_latest_delinquency_month(db_url)
    as_of_str = str(as_of)

    cached = dashboard_query.cache_get(endpoint, as_of_str)
    if cached is not None:
        dashboard_cache_total.labels(endpoint=endpoint, result="hit").inc()
        return Response(
            content=str(cached),
            media_type="application/json",
            headers={"Cache-Control": "max-age=300, public"},
        )
    dashboard_cache_total.labels(endpoint=endpoint, result="miss").inc()

    data = dashboard_query.compose_past_due(as_of, db_url)
    envelope = build_envelope(data, as_of, uuid.UUID(rid))
    json_str = envelope.model_dump_json()

    dashboard_query.cache_set(endpoint, as_of_str, json_str)
    save_dashboard_audit(endpoint, {"as_of": as_of_str}, uuid.UUID(rid), db_url)
    dashboard_request_total.labels(endpoint=endpoint, status="success").inc()
    dashboard_duration_seconds.labels(endpoint=endpoint).observe(time.monotonic() - t0)

    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Cache-Control": "max-age=300, public"},
    )


@router.get(
    "/officer-branch",
    response_model=DashboardEnvelope[OfficerBranchData],
)
async def officer_branch(
    request: Request,
    as_of_date: date | None = Query(default=None),  # noqa: B008
    branch_id: int | None = Query(default=None),  # noqa: B008
    officer_id: str | None = Query(default=None),  # noqa: B008
    tab: str | None = Query(default=None),  # noqa: B008
) -> Response:
    rid: str = request.state.request_id
    t0 = time.monotonic()
    db_url: str = request.app.state.db_url
    endpoint = "officer-branch"

    as_of = as_of_date or repo_loans.fetch_latest_loans_month(db_url)
    as_of_str = f"{as_of}|b={branch_id}|o={officer_id}|t={tab}"

    cached = dashboard_query.cache_get(endpoint, as_of_str)
    if cached is not None:
        dashboard_cache_total.labels(endpoint=endpoint, result="hit").inc()
        return Response(
            content=str(cached),
            media_type="application/json",
            headers={"Cache-Control": "max-age=300, public"},
        )
    dashboard_cache_total.labels(endpoint=endpoint, result="miss").inc()

    data = dashboard_query.compose_officer_branch(
        as_of, db_url, branch_id, officer_id, tab
    )
    envelope = build_envelope(data, as_of, uuid.UUID(rid))
    json_str = envelope.model_dump_json()

    dashboard_query.cache_set(endpoint, as_of_str, json_str)
    save_dashboard_audit(endpoint, {"as_of": as_of_str}, uuid.UUID(rid), db_url)
    dashboard_request_total.labels(endpoint=endpoint, status="success").inc()
    dashboard_duration_seconds.labels(endpoint=endpoint).observe(time.monotonic() - t0)

    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Cache-Control": "max-age=300, public"},
    )


@router.get(
    "/executive-summary",
    response_model=DashboardEnvelope[ExecutiveSummaryData],
)
async def executive_summary(
    request: Request,
    as_of_date: date | None = Query(default=None),  # noqa: B008
) -> Response:
    rid: str = request.state.request_id
    t0 = time.monotonic()
    db_url: str = request.app.state.db_url
    endpoint = "executive-summary"

    as_of = as_of_date or repo_exec.fetch_latest_executive_month(db_url)
    as_of_str = str(as_of)

    cached = dashboard_query.cache_get(endpoint, as_of_str)
    if cached is not None:
        dashboard_cache_total.labels(endpoint=endpoint, result="hit").inc()
        return Response(
            content=str(cached),
            media_type="application/json",
            headers={"Cache-Control": "max-age=300, public"},
        )
    dashboard_cache_total.labels(endpoint=endpoint, result="miss").inc()

    data = executive_query.compose_executive_summary(as_of, db_url)
    envelope = build_envelope(data, as_of, uuid.UUID(rid))
    json_str = envelope.model_dump_json()

    dashboard_query.cache_set(endpoint, as_of_str, json_str)
    save_dashboard_audit(endpoint, {"as_of": as_of_str}, uuid.UUID(rid), db_url)
    dashboard_request_total.labels(endpoint=endpoint, status="success").inc()
    dashboard_duration_seconds.labels(endpoint=endpoint).observe(time.monotonic() - t0)

    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Cache-Control": "max-age=300, public"},
    )
