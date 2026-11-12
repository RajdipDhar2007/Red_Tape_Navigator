"""Deployment helpers: host-generated keys, managed-Postgres URLs, first officer from env, in-process scheduler, calendar export."""
import base64
import re
from datetime import UTC, datetime, timedelta

from cryptography.fernet import Fernet
from sqlalchemy import select

from app.core.config import Settings, production_problems
from app.db.models import AuditLog, NavSession, Reminder, User
from app.db.session import maker
from app.jobs import inprocess
from app.services.bootstrap import ensure_admin

GOOD = dict(
    app_env="prod", secret_key="x" * 40, field_encryption_key=Fernet.generate_key().decode(),
    database_url="postgresql+asyncpg://u:p@db/rtn", cors_origins="https://app.example.in", demo_mode=False,
    grievance_contact="dpo@example.in", web_base_url="https://app.example.in", smtp_host="smtp.example.in",
    smtp_from="no-reply@example.in",
)


def test_standard_base64_key_from_a_host_is_accepted():
    raw = bytes(range(250, 256)) * 5 + b"\xfb\xff"  # 32 bytes that encode with both '+' and '/'
    std = base64.b64encode(raw).decode()
    assert "+" in std and "/" in std
    key = Settings(field_encryption_key=std).field_encryption_key
    assert key == base64.urlsafe_b64encode(raw).decode()
    assert Fernet(key.encode()).decrypt(Fernet(key.encode()).encrypt(b"pan")) == b"pan"
    # rotation lists keep working
    two = Settings(field_encryption_key=f"{std},{std}").field_encryption_key
    assert all(Fernet(k.encode()) for k in two.split(","))


def test_managed_postgres_urls_are_made_asyncpg_safe():
    neon = Settings(database_url="postgresql://u:p@ep-x.aws.neon.tech/db?sslmode=require&channel_binding=require").database_url
    assert neon == "postgresql+asyncpg://u:p@ep-x.aws.neon.tech/db?ssl=require"
    assert Settings(database_url="postgres://u:p@h/db?sslmode=disable").database_url == "postgresql+asyncpg://u:p@h/db"
    assert Settings(database_url="postgresql://u:p@h/db?application_name=rtn").database_url.endswith("?application_name=rtn")
    assert Settings(database_url="sqlite+aiosqlite:///x.db?sslmode=require").database_url.endswith("?sslmode=require")


def test_bootstrap_admin_settings_are_validated_in_prod():
    assert production_problems(Settings(**GOOD)) == []
    assert production_problems(Settings(**GOOD, bootstrap_admin_email="o@example.in", bootstrap_admin_password="long-enough-pass")) == []
    assert any("BOOTSTRAP" in p for p in production_problems(Settings(**GOOD, bootstrap_admin_email="o@example.in")))
    assert any("12 characters" in p for p in production_problems(Settings(**GOOD, bootstrap_admin_email="o@example.in", bootstrap_admin_password="short")))


async def test_first_officer_from_env_creates_then_never_overwrites(client):
    s = Settings(bootstrap_admin_email="Officer@Example.in", bootstrap_admin_password="a-long-first-password")
    async with maker()() as db:
        assert await ensure_admin(db, Settings()) == "skipped"
        assert await ensure_admin(db, Settings(bootstrap_admin_email="o@example.in", bootstrap_admin_password="short")) == "skipped"
        assert await ensure_admin(db, s) == "created"
        assert await ensure_admin(db, s) == "unchanged"
    r = await client.post("/auth/login", json={"email": "officer@example.in", "password": "a-long-first-password"})
    assert r.status_code == 200
    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"})
    assert me.json()["role"] == "admin"

    # an existing citizen is promoted but keeps their own password
    reg = await client.post("/auth/register", json={"email": "citizen@example.in", "password": "citizens-own-password"})
    assert reg.status_code == 201
    async with maker()() as db:
        again = Settings(bootstrap_admin_email="citizen@example.in", bootstrap_admin_password="an-attackers-password")
        assert await ensure_admin(db, again) == "promoted"
    assert (await client.post("/auth/login", json={"email": "citizen@example.in", "password": "an-attackers-password"})).status_code == 401
    assert (await client.post("/auth/login", json={"email": "citizen@example.in", "password": "citizens-own-password"})).status_code == 200


async def test_in_process_scheduler_runs_each_job_once_per_interval(client):
    calls: list[str] = []

    async def ok(db):
        calls.append("ok")

    async def boom(db):
        calls.append("boom")
        raise RuntimeError("provider down")

    jobs = {"fast": (timedelta(minutes=30), ok), "broken": (timedelta(days=1), boom)}
    t0 = datetime.now(UTC)
    assert await inprocess.run_due(t0, jobs) == ["fast", "broken"]  # nothing recorded yet: everything is due
    assert await inprocess.run_due(t0 + timedelta(minutes=5), jobs) == []  # a restart five minutes later repeats nothing
    assert await inprocess.run_due(t0 + timedelta(minutes=31), jobs) == ["fast"]
    assert await inprocess.run_due(t0 + timedelta(days=1, minutes=40), jobs) == ["fast", "broken"]
    assert calls == ["ok", "boom", "ok", "ok", "boom"]
    async with maker()() as db:
        rows = (await db.execute(select(AuditLog).where(AuditLog.action == "job.broken"))).scalars().all()
        assert [r.detail["ok"] for r in rows] == [False, False] and all(r.actor == "system" for r in rows)
        assert await inprocess.last_run(db, "never") is None
    assert set(inprocess.JOBS) == {"reminders", "purge", "refresh_rules", "forms"}

    # the heavy weekly jobs never run at first boot: they are marked and wait one interval
    heavy = {"refresh_rules": (timedelta(days=7), ok)}
    before = len(calls)
    assert await inprocess.run_due(t0, heavy) == [] and len(calls) == before
    assert await inprocess.run_due(t0 + timedelta(days=6), heavy) == []
    assert await inprocess.run_due(datetime.now(UTC) + timedelta(days=7, minutes=1), heavy) == ["refresh_rules"]


async def test_real_reminder_and_purge_jobs_run_in_process(client):
    jobs = {k: inprocess.JOBS[k] for k in ("reminders", "purge")}
    assert await inprocess.run_due(jobs=jobs) == ["reminders", "purge"]
    async with maker()() as db:
        rows = (await db.execute(select(AuditLog).where(AuditLog.action.like("job.%")))).scalars().all()
        assert all(r.detail == {"ok": True} for r in rows) and len(rows) == 2


async def test_reminders_list_and_calendar_export(client, auth):
    headers, _ = auth
    async with maker()() as db:
        me = (await db.execute(select(User).where(User.email == "a@example.com"))).scalar_one()
        ns = NavSession(user_id=me.id, goal="open a bakery in Kolkata")
        db.add(ns)
        await db.commit()
        due = datetime(2027, 3, 14, 4, 30, tzinfo=UTC)
        long_title = "Renew: খাদ্য লাইসেন্স; FSSAI, " + "x" * 90
        db.add_all([
            Reminder(session_id=ns.id, user_id=me.id, title=long_title, due_at=due, kind="renewal"),
            Reminder(session_id=ns.id, user_id=me.id, title="Check status\r\nATTENDEE:mailto:evil@example.com", due_at=due - timedelta(days=30), kind="status"),
        ])
        await db.commit()
        sid = ns.id

    listed = (await client.get(f"/sessions/{sid}/reminders", headers=headers)).json()["items"]
    assert [r["kind"] for r in listed] == ["status", "renewal"] and listed[0]["sent"] is False

    r = await client.get(f"/sessions/{sid}/reminders.ics", headers=headers)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/calendar")
    assert "attachment" in r.headers["content-disposition"] and r.headers["cache-control"] == "no-store"
    body = r.content.decode()
    assert body.startswith("BEGIN:VCALENDAR\r\n") and body.endswith("END:VCALENDAR\r\n")
    assert body.count("BEGIN:VEVENT") == 2 and "DTSTART;VALUE=DATE:20270314" in body and "DTEND;VALUE=DATE:20270315" in body
    assert all(len(line.encode()) <= 75 for line in body.split("\r\n"))  # folded, never mid-character
    unfolded = body.replace("\r\n ", "")
    assert "খাদ্য লাইসেন্স\\; FSSAI\\, " in unfolded
    assert "\r\nATTENDEE" not in body  # a title cannot inject a calendar property
    assert "not legal advice" in unfolded

    # someone else's session stays hidden
    other = await client.post("/auth/register", json={"email": "b@example.com", "password": "correct-horse-battery"})
    oh = {"Authorization": f"Bearer {other.json()['access_token']}"}
    assert (await client.get(f"/sessions/{sid}/reminders.ics", headers=oh)).status_code == 404
    assert (await client.get(f"/sessions/{sid}/reminders", headers=oh)).status_code == 404
    assert (await client.get(f"/sessions/{sid}/reminders.ics")).status_code == 401


async def test_app_starts_and_stops_with_scheduler_and_bootstrap(client, monkeypatch):
    from app.core.config import get_settings
    from app.main import create_app, lifespan

    monkeypatch.setenv("RUN_SCHEDULER", "true")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAIL", "boot@example.in")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "a-long-first-password")
    get_settings.cache_clear()
    try:
        async with lifespan(create_app()):
            async with maker()() as db:
                user = (await db.execute(select(User).where(User.email == "boot@example.in"))).scalar_one()
                assert user.role == "admin"
    finally:
        get_settings.cache_clear()


def test_render_blueprints_only_set_variables_the_app_reads():
    """A typo in a Blueprint would silently leave a setting at its default in production."""
    from pathlib import Path

    import yaml

    root = Path(__file__).resolve().parents[2]
    known = {name.upper() for name in Settings.model_fields} | {"RUN_MIGRATIONS", "SEED_ON_START", "PORT"}
    for name in ("render.yaml", "render.production.yaml"):
        doc = yaml.safe_load((root / name).read_text(encoding="utf-8"))
        groups = {g["name"]: g["envVars"] for g in doc.get("envVarGroups", [])}
        for svc in doc["services"]:
            if svc["type"] == "keyvalue":
                continue
            env: dict[str, dict] = {}
            for item in svc["envVars"]:
                for var in groups[item["fromGroup"]] if "fromGroup" in item else [item]:
                    env[var["key"]] = var
            assert set(env) <= known, f"{name}/{svc['name']}: unknown variables {set(env) - known}"
            values = {k: v.get("value") for k, v in env.items()}
            assert values["APP_ENV"] == "prod" and values["DEMO_MODE"] == "false" and values["TRUST_PROXY"] == "true"
            assert env["SECRET_KEY"].get("generateValue") and env["FIELD_ENCRYPTION_KEY"].get("generateValue")
            assert all(not v.get("value") for k, v in env.items() if "PASSWORD" in k or "SECRET" in k or "AUTHKEY" in k), "no secret may be committed"
            assert doc["databases"][0]["postgresMajorVersion"] == "16"
    free = yaml.safe_load((root / "render.yaml").read_text(encoding="utf-8"))
    api = {v["key"]: v for v in free["services"][0]["envVars"]}
    assert len(free["services"]) == 1 and api["RUN_SCHEDULER"]["value"] == "true" and "REDIS_URL" not in api
    assert api["SMTP_PORT"]["value"] == "2525"  # 587 is blocked on Render's free instances


async def test_every_private_route_refuses_anonymous_callers(client):
    """Walks the whole route table, so a new route cannot be added without sign-in by accident."""
    from app.main import app

    public = {
        "/health", "/health/live", "/ready", "/health/ready", "/metrics", "/auth/register", "/auth/login", "/auth/refresh", "/auth/forgot", "/auth/reset",
        "/auth/verify-email", "/consent/notice", "/privacy/policy", "/webhooks/digio",
    }
    checked = 0
    for path, operations in app.openapi()["paths"].items():
        if path in public:
            continue
        url = re.sub(r"\{\w+\}", "x", path.replace("{decision}", "approve"))
        for method in operations:
            r = await client.request(method.upper(), url, json={})
            assert r.status_code == 401, f"{method} {path} answered {r.status_code} without sign-in"
            checked += 1
    assert checked > 50
