"""Prometheus metrics (exposed at /metrics)."""
from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest

REGISTRY = CollectorRegistry()

HTTP_REQUESTS = Counter("rtn_http_requests_total", "HTTP requests", ["method", "route", "status"], registry=REGISTRY)
HTTP_LATENCY = Histogram("rtn_http_request_seconds", "HTTP latency", ["route"], registry=REGISTRY,
                         buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10))
LLM_CALLS = Counter("rtn_llm_calls_total", "LLM calls", ["outcome"], registry=REGISTRY)
SCRAPES = Counter("rtn_scrapes_total", "Official-site fetches", ["outcome"], registry=REGISTRY)
RATE_LIMITED = Counter("rtn_rate_limited_total", "Requests rejected by the rate limiter", registry=REGISTRY)
LOW_CONFIDENCE = Counter("rtn_low_confidence_claims_total", "Claims routed to human review", registry=REGISTRY)


def render() -> bytes:
    return generate_latest(REGISTRY)
