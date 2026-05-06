"""GET /trust — data freshness and reconciliation health."""

from fastapi import APIRouter, Request
from pydantic import BaseModel

from api.repo.trust import get_trust_stats

router = APIRouter()

_STATIC_CAVEATS: list[str] = [
    "Deposits are sourced from Symitar core only and have no Origence LOS"
    " counterpart — they are excluded from the reconciliation match rate.",
]


class TrustResponse(BaseModel):
    origence_row_count: int
    symitar_row_count: int
    reconciliation_match_rate: float
    known_caveats: list[str]


@router.get("/trust", response_model=TrustResponse)
async def trust(request: Request) -> TrustResponse:
    stats = get_trust_stats(request.app.state.db_url)
    return TrustResponse(
        origence_row_count=stats.origence_row_count,
        symitar_row_count=stats.symitar_row_count,
        reconciliation_match_rate=stats.reconciliation_match_rate,
        known_caveats=list(_STATIC_CAVEATS),
    )
