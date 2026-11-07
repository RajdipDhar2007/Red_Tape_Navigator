"""OpenTelemetry tracing. No-op exporter unless OTEL_EXPORTER_OTLP_ENDPOINT is set. Spans never carry PII."""
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.core.config import get_settings

_configured = False


def configure_tracing() -> None:
    global _configured
    if _configured:
        return
    _configured = True
    provider = TracerProvider(resource=Resource.create({"service.name": "red-tape-navigator"}))
    endpoint = get_settings().otel_exporter_otlp_endpoint
    if endpoint:  # pragma: no cover - needs a collector
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        except ImportError:
            pass
    trace.set_tracer_provider(provider)


@contextmanager
def span(name: str, **attrs: str | int | float | bool):
    with trace.get_tracer("rtn").start_as_current_span(name) as sp:
        for k, v in attrs.items():
            sp.set_attribute(k, v)
        yield sp
