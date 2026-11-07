import json

from app.core.errors import capture_exception
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RateLimiter
from app.core.tracing import configure_tracing, span
from app.main import create_app


async def test_security_headers_and_request_id(client):
    r = await client.get("/health", headers={"X-Request-ID": "abc123"})
    assert r.status_code == 200 and r.json()["disclaimer"]
    assert r.headers["x-request-id"] == "abc123"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert "max-age" in r.headers["strict-transport-security"]
    assert r.headers["cache-control"] == "no-store"


async def test_ready_and_metrics(client):
    r = await client.get("/ready")
    assert r.status_code == 200 and r.json()["database"] is True and "data_region" in r.json()
    await client.get("/health")
    m = await client.get("/metrics")
    assert m.status_code == 200 and "rtn_http_requests_total" in m.text and 'route="/health"' in m.text


async def test_metrics_token_enforced(client, monkeypatch):
    from app.core import config

    monkeypatch.setenv("METRICS_TOKEN", "s3cret")
    config.get_settings.cache_clear()
    try:
        assert (await client.get("/metrics")).status_code == 401
        assert (await client.get("/metrics", headers={"Authorization": "Bearer s3cret"})).status_code == 200
    finally:
        monkeypatch.delenv("METRICS_TOKEN")
        config.get_settings.cache_clear()


async def test_auth_rate_limit_blocks_bruteforce(client):
    codes = []
    for _ in range(25):
        r = await client.post("/auth/login", json={"email": "x@example.com", "password": "wrong-password-1"})
        codes.append(r.status_code)
    assert 429 in codes and codes[0] == 401
    assert (await client.post("/auth/login", json={"email": "x@example.com", "password": "wrong-password-1"})).headers["retry-after"] == "60"


async def test_oversized_body_rejected(client):
    r = await client.post("/auth/login", content=b"x" * 10, headers={"content-length": "2000000", "content-type": "application/json"})
    assert r.status_code == 413


async def test_unhandled_error_does_not_leak(client):
    app = create_app()

    @app.get("/boom")
    async def boom():
        raise RuntimeError("secret internal detail ABCDE1234F")

    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t") as c:
        r = await c.get("/boom")
    assert r.status_code == 500 and r.json() == {"detail": "Internal error"}


def test_rate_limiter_window():
    rl = RateLimiter()
    assert all(rl.allow("k", 3, 10, now=t) for t in (0, 1, 2))
    assert not rl.allow("k", 3, 10, now=3)
    assert rl.allow("k", 3, 10, now=11)  # window slid


def test_logging_redacts_pii(capsys):
    configure_logging("INFO")
    get_logger("t").info("evt", pan="ABCDE1234F", note="aadhaar 2345 6789 0124 ok")
    out = capsys.readouterr().out
    rec = json.loads(out.strip().splitlines()[-1])
    assert rec["pan"] == "[REDACTED]" and "2345 6789 0124" not in out and rec["event"] == "evt"


def test_tracing_span_and_error_capture():
    configure_tracing()
    configure_tracing()  # idempotent
    with span("unit", a=1) as sp:
        assert sp is not None
    capture_exception(ValueError("x"), path="/p")
