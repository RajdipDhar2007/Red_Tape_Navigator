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


def test_rate_limiter_bounded_memory_and_expiry_eviction():
    rl = RateLimiter(max_keys=5)
    for i in range(8):
        assert rl.allow(f"ip-{i}", 2, window=10, now=float(i))
        assert len(rl.hits) <= 5
    # Earliest keys were evicted to maintain max_keys=5
    assert set(rl.hits.keys()) == {"ip-3", "ip-4", "ip-5", "ip-6", "ip-7"}

    # Advance past the 10s window; expired keys are swept and removed
    assert rl.allow("fresh-ip", 2, window=10, now=25.0)
    assert set(rl.hits.keys()) == {"fresh-ip"}
    assert not rl.allow("zero-limit", 0, window=10, now=25.0)


async def test_redis_backed_rate_limiter_shared_across_workers_and_window_reset():
    store: dict[str, int] = {}
    ttls: dict[str, int] = {}

    class FakePipeline:
        def __init__(self) -> None:
            self.ops: list[tuple[str, str, int | None]] = []

        def incr(self, key: str) -> "FakePipeline":
            self.ops.append(("incr", key, None))
            return self

        def expire(self, key: str, ttl: int) -> "FakePipeline":
            self.ops.append(("expire", key, ttl))
            return self

        async def execute(self) -> list[int | bool]:
            out: list[int | bool] = []
            for op, k, arg in self.ops:
                if op == "incr":
                    store[k] = store.get(k, 0) + 1
                    out.append(store[k])
                elif op == "expire" and arg is not None:
                    ttls[k] = arg
                    out.append(True)
            return out

    class FakeRedis:
        def pipeline(self, transaction: bool = True) -> FakePipeline:
            assert transaction is True
            return FakePipeline()

    shared_redis = FakeRedis()
    worker1 = RateLimiter(redis_client=shared_redis)
    worker2 = RateLimiter(redis_client=shared_redis)

    # Limit is 3 across both workers in the same 10-second window
    assert await worker1.allow_async("203.0.113.5:auth", 3, window=10.0, now=100.0) is True
    assert await worker2.allow_async("203.0.113.5:auth", 3, window=10.0, now=101.0) is True
    assert await worker1.allow_async("203.0.113.5:auth", 3, window=10.0, now=102.0) is True
    assert await worker2.allow_async("203.0.113.5:auth", 3, window=10.0, now=103.0) is False
    assert all(v == 11 for v in ttls.values())

    # Next window (now=110.0 -> bucket 11) resets the counter
    assert await worker2.allow_async("203.0.113.5:auth", 3, window=10.0, now=110.0) is True
    assert await worker1.allow_async("203.0.113.5:auth", 0, window=10.0, now=110.0) is False


async def test_redis_rate_limiter_falls_back_safely_when_unreachable(capsys):
    configure_logging("WARNING")
    rl = RateLimiter(max_keys=4, redis_url="redis://127.0.0.1:1/0")
    # Redis is unreachable; falls back cleanly to in-memory limiter and reuses cached client instance
    assert await rl.allow_async("198.51.100.9:auth", 2, window=60.0, now=10.0) is True
    first_client = rl._redis
    assert first_client is not None
    assert await rl.allow_async("198.51.100.9:auth", 2, window=60.0, now=11.0) is True
    assert rl._redis is first_client  # client is cached and not recreated per request
    assert await rl.allow_async("198.51.100.9:auth", 2, window=60.0, now=12.0) is False

    out = capsys.readouterr().out
    assert "rate_limiter_redis_unavailable" in out
    assert "198.51.100.9" not in out  # no IP or sensitive request data in warning logs


def test_logging_redacts_pii(capsys):
    configure_logging("INFO")
    fake_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
    get_logger("t").info(
        "evt",
        pan="ABCDE1234F",
        password="SuperSecretPassword123!",
        anthropic_api_key="sk-ant-secret",
        totp_secret="JBSWY3DPEHPK3PXP",
        raw_bytes=b"%PDF-1.4 secret document bytes",
        unkeyed_blob=b"%PDF-1.4 binary payload",
        note=f"aadhaar 2345 6789 0124 token {fake_jwt} db postgresql://rtn:dbpass123@db.internal:5432/rtn ok",
    )
    out = capsys.readouterr().out
    rec = json.loads(out.strip().splitlines()[-1])
    assert rec["pan"] == "[REDACTED]"
    assert rec["password"] == "[REDACTED]"
    assert rec["anthropic_api_key"] == "[REDACTED]"
    assert rec["totp_secret"] == "[REDACTED]"
    assert rec["raw_bytes"] == "[REDACTED]"
    assert rec["unkeyed_blob"] == "[BINARY-REDACTED]"
    assert "2345 6789 0124" not in out
    assert "SuperSecretPassword123!" not in out
    assert "sk-ant-secret" not in out
    assert "dbpass123" not in out
    assert fake_jwt not in out
    assert "[JWT-REDACTED]" in rec["note"]
    assert "postgresql://rtn:[REDACTED]@db.internal:5432/rtn" in rec["note"]
    assert rec["event"] == "evt"


def test_tracing_span_and_error_capture(capsys):
    from app.core.errors import init_error_tracking

    configure_logging("INFO")
    init_error_tracking()  # SENTRY_DSN is empty -> operates normally without Sentry
    configure_tracing()
    configure_tracing()  # idempotent
    with span("unit", a=1) as sp:
        assert sp is not None
    capture_exception(ValueError("x"), path="/p", authorization="Bearer secret-jwt-value")
    out = capsys.readouterr().out
    assert "secret-jwt-value" not in out


async def test_redis_cache_degrades_to_miss_when_unreachable():
    from app.core.cache import RedisCache

    c = RedisCache("redis://127.0.0.1:1/0")  # nothing listens here
    assert await c.get("k") is None
    await c.set("k", {"a": 1})  # must not raise
    await c.delete("k")


async def test_health_live_and_ready_endpoints_and_degraded_dependencies(client, monkeypatch):
    from app import main as main_mod
    from app.core import config

    # 1. Liveness (/health and /health/live)
    r_live = await client.get("/health/live")
    assert r_live.status_code == 200
    assert r_live.json()["status"] == "ok"
    assert r_live.json()["live"] is True

    # 2. Readiness (/health/ready) with unreachable Redis degrades gracefully while keeping HTTP 200
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:1/0")
    config.get_settings.cache_clear()
    try:
        r_ready = await client.get("/health/ready")
        assert r_ready.status_code == 200
        body = r_ready.json()
        assert body["status"] == "ready"
        assert body["ready"] is True
        assert body["database"] is True
        assert body["redis"] == "degraded"
        assert body["storage_backend"] == "local"
    finally:
        monkeypatch.delenv("REDIS_URL", raising=False)
        config.get_settings.cache_clear()

    # 3. Readiness returns 503 when database is unavailable
    def broken_maker():
        class BrokenCtx:
            async def __aenter__(self):
                raise RuntimeError("db connection refused")

            async def __aexit__(self, *args):
                return False

        return BrokenCtx

    monkeypatch.setattr(main_mod, "maker", lambda: broken_maker)
    r_down = await client.get("/health/ready")
    assert r_down.status_code == 503
    assert r_down.json() == {"status": "unavailable", "ready": False, "database": False}


def test_db_backup_and_restore_readiness_safeguards(tmp_path):
    import sys
    from datetime import UTC, datetime
    from pathlib import Path

    scripts_dir = str(Path(__file__).resolve().parents[2] / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import db_backup_restore as dbr

    fixed_now = datetime(2026, 11, 12, 14, 30, 0, tzinfo=UTC)
    fname = dbr.build_backup_filename(now=fixed_now)
    assert fname == "rtn-backup-20261112T143000Z.dump"

    # 1. Backup plan normalizes asyncpg URL, strips password from CLI args, and sets pgpassword separately
    b_plan = dbr.build_backup_plan(
        "postgresql+asyncpg://rtn:TopSecretPass99@db.example.in:5432/rtn",
        output_dir=tmp_path,
        now=fixed_now,
    )
    assert b_plan.pgpassword == "TopSecretPass99"
    assert all("TopSecretPass99" not in arg for arg in b_plan.args)
    assert all("TopSecretPass99" not in arg for arg in b_plan.redacted_args)
    assert "postgresql://rtn:[REDACTED]@db.example.in:5432/rtn" in b_plan.redacted_args

    # 2. Refuses non-PostgreSQL URLs
    import pytest

    with pytest.raises(dbr.BackupRestoreSafetyError, match="Only PostgreSQL"):
        dbr.build_backup_plan("sqlite+aiosqlite:///./data/rtn.db")

    # 3. Restore refuses when APP_ENV=prod
    with pytest.raises(dbr.BackupRestoreSafetyError, match="APP_ENV is 'prod'"):
        dbr.build_restore_plan(
            dump_file=tmp_path / fname,
            target_url="postgresql://rtn:pw@localhost:5432/rtn_restore",
            app_env="prod",
            confirm_flag=True,
            confirm_env=dbr.CONFIRM_ENV_VALUE,
        )

    # 4. Restore refuses when confirmation flag or env var is missing
    with pytest.raises(dbr.BackupRestoreSafetyError, match="requires both --confirm-non-prod-restore"):
        dbr.build_restore_plan(
            dump_file=tmp_path / fname,
            target_url="postgresql://rtn:pw@localhost:5432/rtn_restore",
            app_env="dev",
            confirm_flag=False,
            confirm_env=dbr.CONFIRM_ENV_VALUE,
        )
    with pytest.raises(dbr.BackupRestoreSafetyError, match="requires both --confirm-non-prod-restore"):
        dbr.build_restore_plan(
            dump_file=tmp_path / fname,
            target_url="postgresql://rtn:pw@localhost:5432/rtn_restore",
            app_env="dev",
            confirm_flag=True,
            confirm_env="",
        )

    # 5. Restore refuses when target matches primary DATABASE_URL
    with pytest.raises(dbr.BackupRestoreSafetyError, match="active primary DATABASE_URL"):
        dbr.build_restore_plan(
            dump_file=tmp_path / fname,
            target_url="postgresql://rtn:pw@localhost:5432/rtn_restore",
            primary_url="postgresql+asyncpg://rtn:pw@localhost:5432/rtn_restore",
            app_env="dev",
            confirm_flag=True,
            confirm_env=dbr.CONFIRM_ENV_VALUE,
        )

    # 6. Restore refuses when target host/db contains prod markers or lacks verification suffix
    with pytest.raises(dbr.BackupRestoreSafetyError, match="production marker"):
        dbr.build_restore_plan(
            dump_file=tmp_path / fname,
            target_url="postgresql://rtn:pw@prod-db.example.in:5432/rtn_restore",
            app_env="dev",
            confirm_flag=True,
            confirm_env=dbr.CONFIRM_ENV_VALUE,
        )
    with pytest.raises(dbr.BackupRestoreSafetyError, match="must end with one of"):
        dbr.build_restore_plan(
            dump_file=tmp_path / fname,
            target_url="postgresql://rtn:pw@localhost:5432/rtn_staging",
            app_env="dev",
            confirm_flag=True,
            confirm_env=dbr.CONFIRM_ENV_VALUE,
        )

    # 7. Valid non-prod restore plan constructs safe pg_restore + psql verification commands
    r_plan = dbr.build_restore_plan(
        dump_file=tmp_path / fname,
        target_url="postgresql://rtn:RestoreSecret88@localhost:5432/rtn_restore",
        primary_url="postgresql://rtn:PrimarySecret99@localhost:5432/rtn_dev",
        app_env="dev",
        confirm_flag=True,
        confirm_env=dbr.CONFIRM_ENV_VALUE,
    )
    assert r_plan.pgpassword == "RestoreSecret88"
    assert all("RestoreSecret88" not in a for a in r_plan.args)
    assert r_plan.verify_args is not None and r_plan.verify_args[0] == "psql"
    dry_res = dbr.execute_plan(r_plan, dry_run=True)
    assert dry_res["ok"] is True and dry_res["dry_run"] is True


async def test_worker_observed_execution_logs_and_captures_failures(capsys):
    import pytest

    from app.jobs.worker import _run_observed, purge_job, reminders_job

    configure_logging("INFO")
    assert isinstance(await purge_job({}), int)
    assert isinstance(await reminders_job({}), int)

    async def failing_job():
        raise RuntimeError("simulated worker failure")

    with pytest.raises(RuntimeError, match="simulated worker failure"):
        await _run_observed("failing_job", failing_job)

    out = capsys.readouterr().out
    assert "worker_job_started" in out
    assert "worker_job_completed" in out
    assert "unhandled_exception" in out

