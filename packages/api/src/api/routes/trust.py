"""GET /trust — data freshness and reconciliation health."""

from fastapi import APIRouter, Request
from nl_engine.context_loader import AllContext
from pydantic import BaseModel

from api.repo.trust import get_trust_stats

router = APIRouter()

_DEPOSIT_CAVEAT = (
    "Deposits are sourced from Symitar core only and have no Origence LOS"
    " counterpart — they are excluded from the reconciliation match rate."
)


class TrustResponse(BaseModel):
    origence_row_count: int
    symitar_row_count: int
    reconciliation_match_rate: float
    known_caveats: list[str]


@router.get("/trust", response_model=TrustResponse)
async def trust(request: Request) -> TrustResponse:
    stats = get_trust_stats(request.app.state.db_url)
    ctx: AllContext = request.app.state.ctx
    caveats = [_DEPOSIT_CAVEAT] + [m.caveats for m in ctx.metrics if m.caveats]
    return TrustResponse(
        origence_row_count=stats.origence_row_count,
        symitar_row_count=stats.symitar_row_count,
        reconciliation_match_rate=stats.reconciliation_match_rate,
        known_caveats=caveats,
    )
