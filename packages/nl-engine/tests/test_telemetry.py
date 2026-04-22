"""Unit tests for telemetry.py — span_stage decorator creates correctly named spans."""

import pytest
from nl_engine.telemetry import span_stage
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


def _make_exporter() -> tuple[TracerProvider, InMemorySpanExporter]:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider, exporter


def test_span_stage_creates_span(monkeypatch: pytest.MonkeyPatch) -> None:
    import nl_engine.telemetry as tel

    provider, exporter = _make_exporter()
    monkeypatch.setattr(tel, "get_tracer", lambda: provider.get_tracer("nl_engine"))

    @span_stage("test_stage")
    def _fn() -> str:
        return "ok"

    result = _fn()

    assert result == "ok"
    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "test_stage"


def test_span_stage_preserves_return_value(monkeypatch: pytest.MonkeyPatch) -> None:
    import nl_engine.telemetry as tel

    provider, _ = _make_exporter()
    monkeypatch.setattr(tel, "get_tracer", lambda: provider.get_tracer("nl_engine"))

    @span_stage("compute")
    def _add(a: int, b: int) -> int:
        return a + b

    assert _add(3, 4) == 7


def test_span_stage_propagates_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    import nl_engine.telemetry as tel

    provider, _ = _make_exporter()
    monkeypatch.setattr(tel, "get_tracer", lambda: provider.get_tracer("nl_engine"))

    @span_stage("failing_stage")
    def _boom() -> None:
        raise ValueError("intentional")

    with pytest.raises(ValueError, match="intentional"):
        _boom()
