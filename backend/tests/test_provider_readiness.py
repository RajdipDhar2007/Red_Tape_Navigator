"""Provider readiness, resilience, timeout, malformed-response, webhook, and /admin/readiness tests.

All external providers (Anthropic LLM, SMTP, MSG91, Digio eSign/DigiLocker, Redis) are tested with mocks/fakes.
No real API keys or live network calls are used.
"""
import asyncio
import hashlib
import hmac
import json
import smtplib
from types import SimpleNamespace

import httpx
import pytest

from app.agent.intake import parse_goal
from app.agent.llm import LLM, ToolSpec, _breaker
from app.agent.research import ExtractedClaims
from app.core.config import Settings, get_settings, production_problems
from app.db.models import User
from app.db.session import maker
from app.integrations.factory import get_digilocker, get_email_sender, get_esign, get_sms_sender
from app.integrations.mock import MockMessenger
from app.integrations.real.digio import BASE_URLS, DigioClient, DigioDigiLocker, DigioESign
from app.integrations.real.msg91 import Msg91Sms
from app.integrations.real.smtp import SmtpEmail
from tests.test_prod_and_fetcher import GOOD

# ---------------- PART 2: AI Provider Hardening ----------------


async def test_llm_redacts_pii_before_sending_and_bounds_retries_and_timeout(capsys):
    _breaker.success()
    seen_prompts: list[str] = []

    class CapturingClient:
        class messages:  # noqa: N801
            @staticmethod
            async def create(**kw):
                for m in kw.get("messages", []):
                    if isinstance(m.get("content"), str):
                        seen_prompts.append(m["content"])
                return SimpleNamespace(
                    stop_reason="tool_use",
                    content=[
                        SimpleNamespace(
                            type="tool_use",
                            id="1",
                            name="emit",
                            input={"claims": []},
                        )
                    ],
                )

    llm = LLM(client=CapturingClient(), model="claude-test", timeout=5.0, retries=1)
    assert llm.available
    await llm.structured(
        "sys",
        "My Aadhaar is 2345 6789 0124 and PAN is ABCDE1234F in Kolkata",
        ExtractedClaims,
    )
    assert len(seen_prompts) == 1
    assert "2345 6789 0124" not in seen_prompts[0]
    assert "ABCDE1234F" not in seen_prompts[0]
    assert "[AADHAAR-REDACTED]" in seen_prompts[0] and "[PAN-REDACTED]" in seen_prompts[0]

    # Timeout and bounded retries (retries=1 -> exactly 2 attempts)
    attempts = {"count": 0}

    class SlowClient:
        class messages:  # noqa: N801
            @staticmethod
            async def create(**kw):
                attempts["count"] += 1
                await asyncio.sleep(0.2)
                return SimpleNamespace(content=[])

    slow_llm = LLM(client=SlowClient(), model="claude-test", timeout=0.03, retries=1)
    with pytest.raises(TimeoutError):
        await slow_llm.structured("sys", "open bakery", ExtractedClaims)
    assert attempts["count"] == 2

    # Intake degrades gracefully to deterministic rules when LLM times out or fails
    parsed = await parse_goal("I want to open a bakery in Kolkata", llm=slow_llm)
    assert parsed.activity == "bakery" and parsed.city == "Kolkata"
    _breaker.success()


async def test_llm_tool_loop_redacts_initial_user_prompt():
    _breaker.success()
    seen: list[str] = []

    class DummyArgs(ExtractedClaims):
        pass

    class FakeClient:
        class messages:  # noqa: N801
            @staticmethod
            async def create(**kw):
                seen.append(str(kw["messages"][0]["content"]))
                return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="ok")])

    async def noop(a):
        return "ok"

    llm = LLM(client=FakeClient(), model="claude-test")
    out = await llm.tool_loop("sys", "PAN ABCDE1234F goal", [ToolSpec("t", "d", DummyArgs, noop)])
    assert out == "ok"
    assert "ABCDE1234F" not in seen[0] and "[PAN-REDACTED]" in seen[0]


# ---------------- PART 3: SMTP Email Readiness ----------------


async def test_smtp_delivery_states_retries_ssl_timeout_and_no_secret_leak(monkeypatch, caplog):
    # 1. Missing config returns not_configured
    unconfigured = SmtpEmail("", 587, "", "", "")
    res_unconf = await unconfigured.send("citizen@example.com", "body")
    assert not res_unconf.ok and res_unconf.data["error"] == "not_configured"
    assert res_unconf.data["delivery_status"] == "not_configured"

    # 2. MockMessenger vs SmtpEmail delivery_status distinction
    MockMessenger.OUTBOX.clear()
    mock_res = await MockMessenger("email").send("citizen@example.com", "hello")
    assert mock_res.ok and mock_res.mock is True
    assert mock_res.data["queued"] is True
    assert mock_res.data["smtp_accepted"] is False
    assert mock_res.data["delivery_status"] == "queued_mock"

    # 3. Transient 421 error retries once and succeeds on attempt 2; port 465 uses SMTP_SSL
    attempts = {"n": 0}

    class FlakySSL:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def login(self, u, p):
            pass

        def send_message(self, msg):
            attempts["n"] += 1
            if attempts["n"] == 1:
                raise smtplib.SMTPResponseException(421, b"4.7.0 Temporary rate limit")
            return {}

    monkeypatch.setattr(smtplib, "SMTP_SSL", FlakySSL)
    smtp_ssl = SmtpEmail("smtp.example.in", 465, "user", "super-secret-smtp-pw", "no-reply@example.in", retries=1)
    ok_res = await smtp_ssl.send("citizen@example.com", "reset link", "Subject")
    assert ok_res.ok and not ok_res.mock and attempts["n"] == 2
    assert ok_res.data["sent"] is True
    assert ok_res.data["smtp_accepted"] is True
    assert ok_res.data["delivery_status"] == "smtp_accepted"
    assert ok_res.data["recipient_delivery_confirmed"] is False

    # 4. Permanent auth failure (535) is NOT retried and never logs password or recipient
    auth_attempts = {"n": 0}

    class AuthFailSMTP:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def starttls(self, context=None):
            pass

        def login(self, u, p):
            auth_attempts["n"] += 1
            raise smtplib.SMTPAuthenticationError(535, f"Auth failed for {u} with {p}".encode())

        def send_message(self, msg):
            return {}

    monkeypatch.setattr(smtplib, "SMTP", AuthFailSMTP)
    with caplog.at_level("WARNING"):
        fail_res = await SmtpEmail(
            "smtp.example.in", 587, "smtp-admin", "MySmtpSecret99!", "no-reply@example.in", retries=2
        ).send("private-citizen@example.com", "secret-reset-token-xyz")
    assert not fail_res.ok and fail_res.data["delivery_status"] == "failed"
    assert auth_attempts["n"] == 1  # permanent auth error is not retried
    assert "MySmtpSecret99!" not in caplog.text
    assert "private-citizen@example.com" not in caplog.text
    assert "secret-reset-token-xyz" not in caplog.text

    # 5. Timeout handling
    class HangingSMTP(AuthFailSMTP):
        def login(self, u, p):
            raise TimeoutError("SMTP timed out")

    monkeypatch.setattr(smtplib, "SMTP", HangingSMTP)
    timeout_res = await SmtpEmail("smtp.example.in", 587, "u", "p", "no-reply@example.in", retries=0).send(
        "c@example.com", "hi"
    )
    assert not timeout_res.ok and timeout_res.data["error"] == "timeout"


# ---------------- PART 4: MSG91 Readiness ----------------


async def test_msg91_missing_config_timeout_and_no_secret_or_otp_leak(monkeypatch, caplog):
    # 1. Missing config
    res_missing = await Msg91Sms("", "").send("9876543210", "Reminder message")
    assert not res_missing.ok and res_missing.data["error"] == "not_configured"

    # 2. Timeout handling (retries once -> 2 attempts, reports reason=timeout, never logs authkey/OTP/phone)
    calls = {"n": 0}
    real_client = httpx.AsyncClient

    def timeout_handler(req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr(
        "app.integrations.real.msg91.httpx.AsyncClient",
        lambda **kw: real_client(transport=httpx.MockTransport(timeout_handler), **kw),
    )
    with caplog.at_level("WARNING"):
        res_to = await Msg91Sms("SECRET_MSG91_KEY_123", "TPL_99", timeout=1.0).send(
            "9876543210", "OTP 849201 do not share"
        )
    assert not res_to.ok
    assert res_to.data["error"] == "provider_unreachable"
    assert res_to.data["reason"] == "timeout"
    assert calls["n"] == 2
    assert "SECRET_MSG91_KEY_123" not in caplog.text
    assert "9876543210" not in caplog.text
    assert "849201" not in caplog.text


# ---------------- PART 5 & 6: Digio / DigiLocker & Webhook Security ----------------


async def test_digio_sandbox_vs_prod_timeout_missing_config_and_malformed_responses():
    # 1. Sandbox vs Production base URLs
    c_sbx = DigioClient("id", "sec", env="sandbox")
    c_prd = DigioClient("id", "sec", env="production")
    assert c_sbx.base == BASE_URLS["sandbox"]
    assert c_prd.base == BASE_URLS["production"]

    # 2. Missing credentials returns not_configured without network call
    c_empty = DigioClient("", "")
    res_empty = await DigioESign(c_empty).get_status("DID1")
    assert not res_empty.ok and res_empty.data["error"] == "not_configured"

    # 3. Timeout reports provider_unreachable + reason=timeout after 2 attempts on read-only status
    attempts = {"n": 0}

    def timeout_handler(req: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        raise httpx.ReadTimeout("digio read timeout")

    c_to = DigioClient("id", "sec", "sandbox", transport=httpx.MockTransport(timeout_handler))
    res_to = await DigioDigiLocker(c_to).get_status("KID1")
    assert not res_to.ok
    assert res_to.data["error"] == "provider_unreachable"
    assert res_to.data["reason"] == "timeout"
    assert attempts["n"] == 2

    # 4. Malformed 200 responses fail safely with malformed_response instead of crashing or faking pending/completed
    malformed_json = DigioClient(
        "id",
        "sec",
        "sandbox",
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json={"signing_parties": "not-a-list"}, headers={"content-type": "application/json"})
        ),
    )
    res_mal_create = await DigioESign(malformed_json).create_request(b"%PDF-1.4", "a.pdf", "u@example.com", "r", "ref1")
    assert not res_mal_create.ok and res_mal_create.data["error"] == "malformed_response"

    res_mal_status = await DigioESign(malformed_json).get_status("DID1")
    assert not res_mal_status.ok and res_mal_status.data["error"] == "malformed_response"

    res_mal_dl_start = await DigioDigiLocker(malformed_json).start_request("u@example.com", "Name", "ref1")
    assert not res_mal_dl_start.ok and res_mal_dl_start.data["error"] == "malformed_response"

    res_mal_dl_status = await DigioDigiLocker(malformed_json).get_status("KID1")
    assert not res_mal_dl_status.ok and res_mal_dl_status.data["error"] == "malformed_response"


async def test_webhook_malformed_nested_payloads_and_oversized_body_fail_safely(client, monkeypatch):
    s = get_settings()
    secret = "whsec-test-key"
    monkeypatch.setattr(s, "digio_webhook_secret", secret)

    def signed_headers(raw: bytes) -> dict[str, str]:
        sig = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        return {"x-digio-checksum": sig, "content-type": "application/json"}

    # 1. Oversized body (> 1 MB) is rejected with 413
    huge = b"a" * 1_000_010
    r_huge = await client.post("/webhooks/digio", content=huge, headers=signed_headers(huge))
    assert r_huge.status_code == 413

    # 2. Malformed envelopes (JSON array, null id, empty id, boolean id, non-dict payload fields) never crash
    malformed_payloads = [
        b"[1, 2, 3]",
        json.dumps({"id": None, "event": "doc.signed"}).encode(),
        json.dumps({"id": "   ", "event": "doc.signed"}).encode(),
        json.dumps({"id": True, "event": "doc.signed"}).encode(),
        json.dumps({"id": "W-1", "event": ""}).encode(),
        json.dumps({"id": "W-2", "event": "doc.signed", "payload": {"document": "not-a-dict"}}).encode(),
        json.dumps(
            {
                "id": "W-3",
                "event": "kyc_request_approved",
                "payload": {"DIGILOCKER_REQUEST": "bad", "KYC_REQUEST": ["bad"]},
            }
        ).encode(),
    ]
    for raw in malformed_payloads:
        resp = await client.post("/webhooks/digio", content=raw, headers=signed_headers(raw))
        assert resp.status_code == 200 and resp.json()["ok"] is True


# ---------------- PART 7 & 8: Operational Readiness Endpoint & Config Parity ----------------


def test_partial_provider_credentials_flagged_in_prod_config():
    assert any(
        "ANTHROPIC" in p
        for p in production_problems(Settings(**{**GOOD, "anthropic_api_key": "sk-ant-123", "anthropic_model": ""}))
    )
    assert any(
        "MSG91" in p
        for p in production_problems(Settings(**{**GOOD, "msg91_authkey": "k123", "msg91_template_id": ""}))
    )
    assert any(
        "DIGIO_CLIENT_ID and DIGIO_CLIENT_SECRET" in p
        for p in production_problems(Settings(**{**GOOD, "digio_client_id": "cid", "digio_client_secret": ""}))
    )


def test_factory_selects_real_or_mock_adapters_based_on_env(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "smtp_host", "")
    monkeypatch.setattr(s, "msg91_authkey", "")
    monkeypatch.setattr(s, "digio_client_id", "")
    assert isinstance(get_email_sender(), MockMessenger)
    assert isinstance(get_sms_sender(), MockMessenger)
    assert get_esign().mock is True
    assert get_digilocker().mock is True

    monkeypatch.setattr(s, "smtp_host", "smtp.example.in")
    monkeypatch.setattr(s, "smtp_from", "no-reply@example.in")
    monkeypatch.setattr(s, "msg91_authkey", "key1")
    monkeypatch.setattr(s, "msg91_template_id", "tpl1")
    monkeypatch.setattr(s, "digio_client_id", "cid1")
    monkeypatch.setattr(s, "digio_client_secret", "csec1")
    assert isinstance(get_email_sender(), SmtpEmail)
    assert isinstance(get_sms_sender(), Msg91Sms)
    assert isinstance(get_esign(), DigioESign)
    assert isinstance(get_digilocker(), DigioDigiLocker)


async def test_admin_readiness_endpoint_access_control_and_secret_safety(client, monkeypatch):
    # 1. Unauthenticated -> 401
    assert (await client.get("/admin/readiness")).status_code == 401

    # 2. Citizen -> 403
    reg = await client.post(
        "/auth/register", json={"email": "citizen-ready@example.com", "password": "correct-horse-battery"}
    )
    citizen_headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    assert (await client.get("/admin/readiness", headers=citizen_headers)).status_code == 403

    # 3. Promote to admin -> 200 with full readiness matrix and zero secret values leaked
    async with maker()() as db:
        u = (await db.execute(User.__table__.select().where(User.email == "citizen-ready@example.com"))).first()
        user_obj = await db.get(User, u.id)
        user_obj.role = "admin"
        await db.commit()

    s = get_settings()
    monkeypatch.setattr(s, "anthropic_api_key", "TOP_SECRET_ANTHROPIC_KEY")
    monkeypatch.setattr(s, "anthropic_model", "claude-3-5-sonnet")
    monkeypatch.setattr(s, "smtp_host", "smtp.example.in")
    monkeypatch.setattr(s, "smtp_from", "no-reply@example.in")
    monkeypatch.setattr(s, "smtp_username", "smtp-user")
    monkeypatch.setattr(s, "smtp_password", "TOP_SECRET_SMTP_PASS")
    monkeypatch.setattr(s, "msg91_authkey", "TOP_SECRET_MSG91_KEY")
    monkeypatch.setattr(s, "msg91_template_id", "DLT_TPL_1")
    monkeypatch.setattr(s, "digio_client_id", "DIGIO_ID_1")
    monkeypatch.setattr(s, "digio_client_secret", "TOP_SECRET_DIGIO_SECRET")
    monkeypatch.setattr(s, "digio_webhook_secret", "TOP_SECRET_WEBHOOK_KEY")

    r = await client.get("/admin/readiness", headers=citizen_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["application"]["running"] is True
    assert body["database"]["reachable"] is True
    assert body["storage"]["backend"] == "local" and body["storage"]["configured"] is True
    assert body["providers"]["llm"]["configured"] is True
    assert body["providers"]["smtp"]["configured"] is True and body["providers"]["smtp"]["mode"] == "live"
    assert body["providers"]["msg91"]["configured"] is True and body["providers"]["msg91"]["mode"] == "live"
    assert body["providers"]["digio"]["configured"] is True and body["providers"]["digio"]["mode"] == "live"
    assert body["providers"]["digio"]["webhook_secret_configured"] is True
    assert body["providers"]["digio"]["digilocker_field_mapping_ready"] is False

    raw_text = r.text
    for secret_val in (
        "TOP_SECRET_ANTHROPIC_KEY",
        "TOP_SECRET_SMTP_PASS",
        "TOP_SECRET_MSG91_KEY",
        "TOP_SECRET_DIGIO_SECRET",
        "TOP_SECRET_WEBHOOK_KEY",
        s.secret_key,
    ):
        assert secret_val not in raw_text
