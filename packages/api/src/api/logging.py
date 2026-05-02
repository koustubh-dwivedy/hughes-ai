import contextvars
from typing import Any

import structlog
import structlog.contextvars
import structlog.processors
import structlog.stdlib

_request_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default=""
)
_session_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "session_id", default=""
)


def bind_request_id(request_id: str) -> contextvars.Token[str]:
    """Set request_id on the current context; call reset(token) to clear."""
    return _request_id.set(request_id)


def bind_session_id(session_id: str) -> contextvars.Token[str]:
    """Set session_id (X-Hughes-Session) on the current context."""
    return _session_id.set(session_id)


def _inject_request_id(
    logger: Any, method: str, event_dict: structlog.types.EventDict
) -> structlog.types.EventDict:
    rid = _request_id.get()
    if rid:
        event_dict["request_id"] = rid
    sid = _session_id.get()
    if sid:
        event_dict["session_id"] = sid
    return event_dict


structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        _inject_request_id,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)


def get_logger() -> structlog.stdlib.BoundLogger:
    return structlog.stdlib.get_logger()
