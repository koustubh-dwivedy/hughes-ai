"""OTel TracerProvider setup and span_stage decorator for NL engine pipeline."""

import functools
import os
from collections.abc import Callable
from typing import Any, TypeVar

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_F = TypeVar("_F", bound=Callable[..., Any])

_provider = TracerProvider()
_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
_exporter = OTLPSpanExporter(endpoint=_endpoint, insecure=True)
_provider.add_span_processor(BatchSpanProcessor(_exporter))
trace.set_tracer_provider(_provider)


def get_tracer() -> trace.Tracer:
    return trace.get_tracer("nl_engine")


def span_stage(stage: str) -> Callable[[_F], _F]:
    """Decorator that wraps a pipeline stage function with a named OTel span."""
    def decorator(fn: _F) -> _F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with get_tracer().start_as_current_span(stage):
                return fn(*args, **kwargs)
        return wrapper  # type: ignore[return-value]
    return decorator
