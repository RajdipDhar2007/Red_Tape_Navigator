import re
import smtplib

from app.core.security import create_reset_token
from app.db.models import User
from app.db.session import maker
from app.integrations.mock import MockMessenger
from app.integrations.real.smtp import SmtpEmail

PW = "correct-horse-battery"


async def _register(client, email="a@example.com", language="en"):
    r = await client.post("/auth/register", json={"email": email, "password": PW, "language": language})
    assert r.status_code == 201
    return r.json()


def _token_from_outbox() -> str:
    mail = MockMessenger.OUTBOX[-1]
    return re.search(r"token=([\w.\-]+)", mail["text"]).group(1)


async def test_forgot_does_not_reveal_whether_email_exists(client):
    await _register(client)
    MockMessenger.OUTBOX.clear()
    known = await client.post("/auth/forgot", json={"email": "a@example.com"})
    unknown = await client.post("/auth/forgot", json={"email": "nobody@example.com"})
    assert known.status_code == unknown.status_code == 202 and known.json() == unknown.json()
    assert len(MockMessenger.OUTBOX) == 1 and MockMessenger.OUTBOX[0]["to"] == "a@example.com"


async def test_reset_flow_sets_password_signs_out_and_link_is_single_use(client):
    tokens = await _register(client, language="hi")
    MockMessenger.OUTBOX.clear()
    await client.post("/auth/forgot", json={"email": "a@example.com"})
    assert "/hi/reset?token=" in MockMessenger.OUTBOX[-1]["text"]
    token = _token_from_outbox()

    assert (await client.post("/auth/reset", json={"token": token, "password": "a-brand-new-passphrase"})).status_code == 200
    # old refresh token no longer works; old password no longer works; new one does
    assert (await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})).status_code == 401
    assert (await client.post("/auth/login", json={"email": "a@example.com", "password": PW})).status_code == 401
    assert (await client.post("/auth/login", json={"email": "a@example.com", "password": "a-brand-new-passphrase"})).status_code == 200
    # the same link cannot be used twice
    assert (await client.post("/auth/reset", json={"token": token, "password": "yet-another-passphrase"})).status_code == 400


async def test_reset_rejects_garbage_wrong_type_and_short_password(client):
    tokens = await _register(client)
    assert (await client.post("/auth/reset", json={"token": "x" * 40, "password": "a-brand-new-passphrase"})).status_code == 400
    # an access token must not work as a reset token
    r = await client.post("/auth/reset", json={"token": tokens["access_token"], "password": "a-brand-new-passphrase"})
    assert r.status_code == 400
    MockMessenger.OUTBOX.clear()
    await client.post("/auth/forgot", json={"email": "a@example.com"})
    assert (await client.post("/auth/reset", json={"token": _token_from_outbox(), "password": "short"})).status_code == 422


async def test_reset_token_for_deleted_user_is_rejected(client):
    await _register(client)
    async with maker()() as db:
        u = (await db.execute(User.__table__.select())).first()
        user = await db.get(User, u.id)
        token = create_reset_token(user.id, user.password_hash)
        from datetime import UTC, datetime

        user.deleted_at = datetime.now(UTC)
        await db.commit()
    assert (await client.post("/auth/reset", json={"token": token, "password": "a-brand-new-passphrase"})).status_code == 400


async def test_change_password(client):
    tokens = await _register(client)
    h = {"Authorization": f"Bearer {tokens['access_token']}"}
    bad = await client.post("/auth/change-password", json={"current_password": "wrong-password-1", "new_password": "a-brand-new-passphrase"}, headers=h)
    assert bad.status_code == 403
    ok = await client.post("/auth/change-password", json={"current_password": PW, "new_password": "a-brand-new-passphrase"}, headers=h)
    assert ok.status_code == 200 and ok.json()["access_token"]
    assert (await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})).status_code == 401
    assert (await client.post("/auth/login", json={"email": "a@example.com", "password": "a-brand-new-passphrase"})).status_code == 200


class _FakeSMTP:
    sent: list = []
    logged_in: tuple | None = None
    tls = False

    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def starttls(self, context=None):
        _FakeSMTP.tls = True

    def login(self, u, p):
        _FakeSMTP.logged_in = (u, p)

    def send_message(self, msg):
        _FakeSMTP.sent.append(msg)


async def test_smtp_sender_delivers_with_tls_and_login(monkeypatch):
    _FakeSMTP.sent.clear()
    monkeypatch.setattr(smtplib, "SMTP", _FakeSMTP)
    res = await SmtpEmail("smtp.example.in", 587, "user", "pw", "no-reply@example.in").send("c@example.com", "hello", "Subject")
    assert res.ok and not res.mock
    msg = _FakeSMTP.sent[0]
    assert msg["To"] == "c@example.com" and msg["Subject"] == "Subject" and msg["From"] == "no-reply@example.in"
    assert _FakeSMTP.tls and _FakeSMTP.logged_in == ("user", "pw")


async def test_smtp_sender_reports_failure_and_blocks_header_injection(monkeypatch):
    class Boom(_FakeSMTP):
        def send_message(self, msg):
            raise smtplib.SMTPException("down")

    monkeypatch.setattr(smtplib, "SMTP", Boom)
    s = SmtpEmail("smtp.example.in", 587, "", "", "no-reply@example.in")
    assert (await s.send("c@example.com", "x")).ok is False
    assert (await s.send("c@example.com\nBcc: evil@example.com", "x")).ok is False


async def test_dispatch_survives_a_channel_that_raises(client):
    from datetime import UTC, datetime, timedelta

    from app.db.models import Consent, NavSession, Reminder
    from app.followup.reminders import dispatch_due
    from app.integrations.interfaces import Integrations
    from app.integrations.mock import MockDigiLocker, MockESign, MockUMANG

    class Broken:
        channel = "sms"

        async def send(self, to, text, subject=""):
            raise NotImplementedError

    async with maker()() as db:
        u = User(email="r@example.com", password_hash="x")
        db.add(u)
        await db.commit()
        ns = NavSession(user_id=u.id, goal="open a bakery")
        db.add(ns)
        db.add(Consent(user_id=u.id, purpose="reminders", policy_version="1", granted=True))
        await db.commit()
        past = datetime.now(UTC) - timedelta(days=1)
        for ch in ("sms", "email"):
            db.add(Reminder(session_id=ns.id, user_id=u.id, title="t", due_at=past, channel=ch, destination="d@example.com"))
        await db.commit()
        integ = Integrations(MockDigiLocker(), MockESign(), MockUMANG(), {"sms": Broken(), "email": MockMessenger("email")}, "mock")
        assert await dispatch_due(db, integ) == 1  # email still delivered despite the broken sms channel
