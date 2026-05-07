"""POST /log — structured log ingestion endpoint for frontend events."""

from typing import Literal

import structlog
from fastapi import APIRouter, Response
from pydantic import BaseModel

router = APIRouter()

_LEVELS: set[str] = {"error", "warn", "info"}


class LogRequest(BaseModel):
    level: Literal["error", "warn", "info"]
    message: str
    request_id: str = ""
    context: dict[str, object] = {}


@router.post("/log", status_code=204)
async def log_endpoint(body: LogRequest) -> Response:
    log = structlog.stdlib.get_logger()
    bound = log.bind(source="frontend", **body.context)
    if body.request_id:
        # client_request_id preserves the original turn / thread request ID
        # alongside the middleware-generated request_id for this /log call.
        bound = bound.bind(client_request_id=body.request_id)
    if body.level == "error":
        bound.error(body.message)
    elif body.level == "warn":
        bound.warning(body.message)
    else:
        bound.info(body.message)
    return Response(status_code=204)
