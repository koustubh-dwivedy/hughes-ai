"""GET /trust — data freshness and reconciliation health."""

from fastapi import APIRouter, Request
from nl_engine.context_loader import AllContext
from pydantic import BaseModel

from api.repo.trust import get_trust_stats

router = APIRouter()


class TrustResponse(BaseModel):
    origence_row_count: int
    symitar_row_count: int
    reconciliation_match_rate: float
    known_caveats: list[str]


@router.get("/trust", response_model=TrustResponse)
async def trust(request: Request) -> TrustResponse:
    stats = get_trust_stats(request.app.state.db_url)
    ctx: AllContext = request.app.state.ctx
    caveats = [m.caveats for m in ctx.metrics if m.caveats]
    return TrustResponse(
        origence_row_count=stats.origence_row_count,
        symitar_row_count=stats.symitar_row_count,
        reconciliation_match_rate=stats.reconciliation_match_rate,
        known_caveats=caveats,
    )
