"""Middleware that stamps every request with a UUID and propagates it.

Also reads the `X-Hughes-Session` header from the frontend so backend
log records can be correlated with frontend telemetry events that
share the same per-tab session id.
"""

import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from api.logging import (
    _request_id,
    _session_id,
    bind_request_id,
    bind_session_id,
)

SESSION_HEADER = "X-Hughes-Session"


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        rid = str(uuid.uuid4())
        request.state.request_id = rid
        sid = request.headers.get(SESSION_HEADER, "")
        request.state.session_id = sid
        rid_token = bind_request_id(rid)
        sid_token = bind_session_id(sid)
        try:
            response = await call_next(request)
        finally:
            _request_id.reset(rid_token)
            _session_id.reset(sid_token)
        response.headers["X-Request-ID"] = rid
        if sid:
            response.headers[SESSION_HEADER] = sid
        return response
