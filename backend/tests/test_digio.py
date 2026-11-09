"""Digio adapters (mocked HTTP), the webhook (checksum / duplicates / IP), and the API flow around them.

No network is used: httpx.MockTransport plays Digio. Endpoint paths and field names come from documentation.digio.in.
"""
import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.db.models import ExternalRequest
from app.db.session import maker
from app.integrations.interfaces import Integrations
from app.integrations.mock import MockMessenger, MockUMANG
from app.integrations.real.digio import DigioClient, DigioDigiLocker, DigioESign
from tests.test_api_flow import start

PDF = b"%PDF-1.4 fake signed pdf"
SECRET = "whsec-for-tests"


def digio_client(handler) -> DigioClient:
    return DigioClient("cid", "csecret", "sandbox", transport=httpx.MockTransport(handler))


def basic(request: httpx.Request) -> tuple[str, str]:
    raw = base64.b64decode(request.headers["authorization"].split()[1]).decode()
    return tuple(raw.split(":", 1))  # type: ignore[return-value]


# ---------------- eSign adapter ----------------


async def test_esign_create_request_shape_and_result():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"], seen["auth"], seen["body"] = str(request.url), basic(request), request.content
        return httpx.Response(200, json={"id": "DID123", "agreement_status": "requested",
                                         "signing_parties": [{"identifier": "a@example.com", "authentication_url": "https://ext.digio.in/sign/xyz"}]})

    res = await DigioESign(digio_client(handler)).create_request(PDF, "fssai_form_a.pdf", "a@example.com", "I sign", "ref-1")
    assert res.ok and not res.mock
    assert res.data == {"document_id": "DID123", "status": "pending", "signing_url": "https://ext.digio.in/sign/xyz", "legally_valid": False}
    assert seen["url"] == "https://ext.digio.in:444/v2/client/document/upload" and seen["auth"] == ("cid", "csecret")
    body = seen["body"]
    assert b'name="file"' in body and PDF in body
    req = json.loads(body.split(b'name="request"')[1].split(b"\r\n\r\n", 1)[1].split(b"\r\n--")[0])
    assert req["signers"] == [{"identifier": "a@example.com", "reason": "I sign", "sign_type": "aadhaar"}]
    assert req["callback"] == "ref-1" and req["include_authentication_url"] is True and req["will_self_sign"] is False
    assert req["file_name"] == "fssai_form_a.pdf" and req["notify_signers"] is True


async def test_esign_error_gets_friendly_message_and_no_identifiers_logged(caplog):
    def handler(request):
        return httpx.Response(400, json={"code": "1079", "message": "Signer is not valid for a@example.com"})

    with caplog.at_level("WARNING"):
        res = await DigioESign(digio_client(handler)).create_request(PDF, "f.pdf", "a@example.com", "r", "ref")
    assert not res.ok and res.data["code"] == "1079" and "signer details" in res.label
    assert "a@example.com" not in caplog.text and "csecret" not in caplog.text


async def test_esign_unreachable_and_unknown_error_code():
    def boom(request):
        raise httpx.ConnectError("down")

    res = await DigioESign(digio_client(boom)).get_status("DID1")
    assert not res.ok and res.data["error"] == "provider_unreachable"
    res = await DigioESign(digio_client(lambda r: httpx.Response(500, json={"code": "9999"}))).get_status("DID1")
    assert not res.ok and res.data["http_status"] == 500 and "Try again later" in res.label


@pytest.mark.parametrize("agreement,expected", [("requested", "pending"), ("completed", "completed"), ("expired", "expired"), ("failed", "failed")])
async def test_esign_status_mapping(agreement, expected):
    def handler(request):
        assert request.url.path == "/v2/client/document/DID1" and request.method == "GET"
        return httpx.Response(200, json={"id": "DID1", "agreement_status": agreement, "signing_parties": [{"status": "requested"}]})

    assert (await DigioESign(digio_client(handler)).get_status("DID1")).data["status"] == expected


async def test_esign_all_signers_failed_means_failed():
    h = lambda r: httpx.Response(200, json={"agreement_status": "requested", "signing_parties": [{"status": "failed"}]})  # noqa: E731
    assert (await DigioESign(digio_client(h)).get_status("DID1")).data["status"] == "failed"


async def test_esign_download_requires_a_real_pdf():
    def ok(request):
        assert request.url.path == "/v2/client/document/download" and request.url.params["document_id"] == "DID1"
        return httpx.Response(200, content=PDF, headers={"content-type": "application/pdf"})

    assert (await DigioESign(digio_client(ok)).download_signed("DID1")).data["pdf"] == PDF
    html = lambda r: httpx.Response(200, content=b"<html>login</html>", headers={"content-type": "text/html"})  # noqa: E731
    assert not (await DigioESign(digio_client(html)).download_signed("DID1")).ok


# ---------------- DigiLocker adapter ----------------


async def test_digilocker_start_and_status():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.url.path.endswith("with_template"):
            body = json.loads(request.content)
            assert body["template_name"] == "DIGILOCKER_AADHAAR_PAN" and body["customer_identifier"] == "a@example.com"
            assert body["notify_customer"] is True and body["reference_id"] == "ref-9"
            return httpx.Response(200, json={"id": "KID1", "status": "requested"})
        return httpx.Response(200, json={"id": "KID1", "status": "approved"})

    dl = DigioDigiLocker(digio_client(handler))
    started = await dl.start_request("a@example.com", "", "ref-9")
    assert started.ok and started.data == {"request_id": "KID1", "status": "pending", "fields": {}}
    done = await dl.get_status("KID1")
    assert done.data["status"] == "completed" and done.data["fields"] == {}  # field mapping intentionally not guessed
    assert calls == [("POST", "/client/kyc/v2/request/with_template"), ("POST", "/client/kyc/v2/KID1/response")]


@pytest.mark.parametrize("raw,expected", [("rejected", "rejected"), ("failed", "failed"), ("expired", "expired"), ("approval_pending", "pending"), ("skipped", "failed")])
async def test_digilocker_status_mapping(raw, expected):
    h = lambda r: httpx.Response(200, json={"status": raw})  # noqa: E731
    assert (await DigioDigiLocker(digio_client(h)).get_status("K")).data["status"] == expected


# ---------------- webhook ----------------


def sign(body: bytes, secret: str = SECRET) -> dict:
    return {"x-digio-checksum": hmac.new(secret.encode(), body, hashlib.sha256).hexdigest(), "content-type": "application/json"}


@pytest.fixture
def digio_env(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "digio_webhook_secret", SECRET)
    return s


async def add_request(client, auth, external_id="DID777", kind="esign") -> str:
    headers, s = await start(client, auth)
    async with maker()() as db:
        row = ExternalRequest(user_id="u", session_id=s["id"], provider="digio", kind=kind, external_id=external_id, meta={"form_id": "f"})
        db.add(row)
        await db.commit()
        return row.id


async def status_of(rid) -> str:
    async with maker()() as db:
        return (await db.get(ExternalRequest, rid)).status


def sign_event(event="doc.signed", doc="DID777", wid="WHN1") -> bytes:
    return json.dumps({"id": wid, "created_at": 1, "event": event, "entities": ["document"], "payload": {"document": {"id": doc, "error_code": "ESP-1" if "fail" in event else None}}}).encode()


async def test_webhook_refuses_bad_or_missing_checksum_and_unconfigured(client, auth, digio_env, monkeypatch):
    body = sign_event()
    assert (await client.post("/webhooks/digio", content=body)).status_code == 401
    assert (await client.post("/webhooks/digio", content=body, headers=sign(body, "wrong"))).status_code == 401
    monkeypatch.setattr(digio_env, "digio_webhook_secret", "")
    assert (await client.post("/webhooks/digio", content=body, headers=sign(body))).status_code == 503


async def test_webhook_marks_signed_and_is_idempotent(client, auth, digio_env):
    rid = await add_request(client, auth)
    body = sign_event()
    r = await client.post("/webhooks/digio", content=body, headers=sign(body))
    assert r.status_code == 200 and await status_of(rid) == "completed"
    again = await client.post("/webhooks/digio", content=body, headers=sign(body))
    assert again.status_code == 200 and again.json().get("duplicate") is True


async def test_webhook_failed_records_error_code_and_late_partial_does_not_undo(client, auth, digio_env):
    rid = await add_request(client, auth)
    body = sign_event("doc.sign.failed", wid="WHN2")
    assert (await client.post("/webhooks/digio", content=body, headers=sign(body))).status_code == 200
    async with maker()() as db:
        row = await db.get(ExternalRequest, rid)
        assert row.status == "failed" and row.meta["error_code"] == "ESP-1"
    kyc = json.dumps({"id": "WHN3", "event": "DOCUMENTS_PULLED_PARTIALLY", "payload": {"DIGILOCKER_REQUEST": {"id": "RID", "kyc_request_id": "DID777"}}}).encode()
    assert (await client.post("/webhooks/digio", content=kyc, headers=sign(kyc))).status_code == 200
    assert await status_of(rid) == "failed"


async def test_webhook_digilocker_matches_by_kyc_id_or_our_reference(client, auth, digio_env):
    rid = await add_request(client, auth, external_id="KID5", kind="digilocker")
    body = json.dumps({"id": "WHN4", "event": "DOCUMENTS_PULLED_SUCCESSFULLY",
                       "payload": {"DIGILOCKER_REQUEST": {"id": "RID9", "kyc_request_id": "KID5", "reference_id": rid, "state": "COMPLETED"}}}).encode()
    assert (await client.post("/webhooks/digio", content=body, headers=sign(body))).status_code == 200
    assert await status_of(rid) == "completed"


async def test_webhook_unknown_entity_and_garbage_still_200(client, auth, digio_env):
    body = sign_event(doc="DID-UNKNOWN", wid="WHN5")
    assert (await client.post("/webhooks/digio", content=body, headers=sign(body))).status_code == 200
    junk = b"not json"
    assert (await client.post("/webhooks/digio", content=junk, headers=sign(junk))).status_code == 200


async def test_webhook_source_ip_enforced_only_behind_trusted_proxy(client, auth, digio_env, monkeypatch):
    body = sign_event(wid="WHN6")
    monkeypatch.setattr(digio_env, "digio_webhook_ips", "35.154.20.28")
    monkeypatch.setattr(digio_env, "trust_proxy", True)
    assert (await client.post("/webhooks/digio", content=body, headers={**sign(body), "x-forwarded-for": "6.6.6.6"})).status_code == 403
    assert (await client.post("/webhooks/digio", content=body, headers={**sign(body), "x-forwarded-for": "35.154.20.28"})).status_code == 200


# ---------------- API flow with the real adapter (mocked Digio) ----------------


@pytest.fixture
def digio_api(monkeypatch):
    """Route the sessions API to DigioESign/DigioDigiLocker backed by a fake Digio."""
    state = {"uploads": 0, "doc_status": "requested"}

    def handler(request: httpx.Request) -> httpx.Response:
        p = request.url.path
        if p == "/v2/client/document/upload":
            state["uploads"] += 1
            return httpx.Response(200, json={"id": "DIDAPI1", "agreement_status": "requested",
                                             "signing_parties": [{"authentication_url": "https://ext.digio.in/sign/abc"}]})
        if p == "/v2/client/document/download":
            return httpx.Response(200, content=PDF, headers={"content-type": "application/pdf"})
        if p.startswith("/v2/client/document/"):
            return httpx.Response(200, json={"agreement_status": state["doc_status"]})
        if p.endswith("with_template"):
            return httpx.Response(200, json={"id": "KIDAPI1", "status": "requested"})
        return httpx.Response(200, json={"status": "approved"})

    c = digio_client(handler)
    integ = Integrations(DigioDigiLocker(c), DigioESign(c), MockUMANG(), {"email": MockMessenger("email")}, "real")
    monkeypatch.setattr("app.api.sessions.get_integrations", lambda: integ)
    monkeypatch.setattr(get_settings(), "demo_mode", False)
    return state


async def reviewed_session(client, auth):
    headers, s = await start(client, auth)
    sid = s["id"]
    await client.post(f"/sessions/{sid}/research", json={}, headers=headers)
    from app.db.models import NavSession

    async with maker()() as db:
        ns = await db.get(NavSession, sid)
        ns.reviewed_at = datetime.now(UTC)
        await db.commit()
    return headers, sid


async def test_esign_api_needs_consent_then_signing_link_webhook_and_download(client, auth, digio_api, digio_env):
    headers, sid = await reviewed_session(client, auth)
    # a real provider gets nothing until the citizen consents to sharing with it
    r = await client.post(f"/sessions/{sid}/esign", json={"form_id": "fssai_form_a"}, headers=headers)
    assert r.status_code == 403 and r.json()["detail"]["code"] == "consent_required" and digio_api["uploads"] == 0
    await client.post("/consent", json={"purpose": "identity_providers", "granted": True}, headers=headers)

    r = await client.post(f"/sessions/{sid}/esign", json={"form_id": "fssai_form_a"}, headers=headers)
    assert r.status_code == 200, r.text
    es = r.json()
    assert es["mock"] is False and es["status"] == "pending" and es["signing_url"] == "https://ext.digio.in/sign/abc"
    rid = es["request_id"]

    # not signed yet: polling keeps it pending and the file is withheld
    assert (await client.get(f"/sessions/{sid}/esign/{rid}", headers=headers)).json()["status"] == "pending"
    assert (await client.get(f"/sessions/{sid}/esign/{rid}/signed.pdf", headers=headers)).status_code == 409

    # Digio's webhook says it is signed
    body = sign_event(doc="DIDAPI1", wid="WHN-API")
    assert (await client.post("/webhooks/digio", content=body, headers=sign(body))).status_code == 200
    assert (await client.get(f"/sessions/{sid}/esign/{rid}", headers=headers)).json()["status"] == "completed"
    pdf = await client.get(f"/sessions/{sid}/esign/{rid}/signed.pdf", headers=headers)
    assert pdf.status_code == 200 and pdf.content == PDF and pdf.headers["cache-control"] == "no-store"


async def test_esign_status_falls_back_to_polling_when_webhook_is_late(client, auth, digio_api, digio_env):
    headers, sid = await reviewed_session(client, auth)
    await client.post("/consent", json={"purpose": "identity_providers", "granted": True}, headers=headers)
    rid = (await client.post(f"/sessions/{sid}/esign", json={"form_id": "fssai_form_a"}, headers=headers)).json()["request_id"]
    digio_api["doc_status"] = "completed"
    assert (await client.get(f"/sessions/{sid}/esign/{rid}", headers=headers)).json()["status"] == "completed"


async def test_requests_are_private_to_their_session_and_owner(client, auth, digio_api, digio_env):
    headers, sid = await reviewed_session(client, auth)
    await client.post("/consent", json={"purpose": "identity_providers", "granted": True}, headers=headers)
    rid = (await client.post(f"/sessions/{sid}/esign", json={"form_id": "fssai_form_a"}, headers=headers)).json()["request_id"]
    other = await client.post("/auth/register", json={"email": "b@example.com", "password": "correct-horse-battery"})
    oh = {"Authorization": f"Bearer {other.json()['access_token']}"}
    assert (await client.get(f"/sessions/{sid}/esign/{rid}", headers=oh)).status_code in (403, 404)
    assert (await client.get(f"/sessions/{sid}/documents/digilocker/{rid}", headers=headers)).status_code == 404  # wrong kind


async def test_digilocker_api_starts_request_and_reports_status(client, auth, digio_api):
    headers, s = await start(client, auth)
    sid = s["id"]
    assert (await client.post(f"/sessions/{sid}/documents/digilocker", headers=headers)).status_code == 403  # needs consent
    await client.post("/consent", json={"purpose": "identity_providers", "granted": True}, headers=headers)
    r = (await client.post(f"/sessions/{sid}/documents/digilocker", headers=headers)).json()
    assert r["mock"] is False and r["status"] == "pending" and r["imported"] == []
    assert (await client.get(f"/sessions/{sid}/documents/digilocker/{r['request_id']}", headers=headers)).json()["status"] == "completed"


async def test_provider_failure_is_a_clean_502_and_leaves_no_request(client, auth, monkeypatch, digio_env):
    headers, sid = await reviewed_session(client, auth)
    await client.post("/consent", json={"purpose": "identity_providers", "granted": True}, headers=headers)
    c = digio_client(lambda r: httpx.Response(400, json={"code": "1015"}))
    integ = Integrations(DigioDigiLocker(c), DigioESign(c), MockUMANG(), {}, "real")
    monkeypatch.setattr("app.api.sessions.get_integrations", lambda: integ)
    monkeypatch.setattr(get_settings(), "demo_mode", False)
    r = await client.post(f"/sessions/{sid}/esign", json={"form_id": "fssai_form_a"}, headers=headers)
    assert r.status_code == 502 and r.json()["detail"]["code"] == "provider_error"
    async with maker()() as db:
        assert (await db.execute(select(ExternalRequest))).scalars().first() is None


async def test_mock_esign_still_labelled_and_in_prod_without_provider_is_refused(client, auth, monkeypatch):
    headers, sid = await reviewed_session(client, auth)
    r = (await client.post(f"/sessions/{sid}/esign", json={"form_id": "fssai_form_a"}, headers=headers)).json()
    assert r["mock"] and "Demo mode" in r["label"] and r["legally_valid"] is False
    assert (await client.get(f"/sessions/{sid}/esign/{r['request_id']}/signed.pdf", headers=headers)).status_code == 404
    monkeypatch.setattr(get_settings(), "demo_mode", False)
    assert (await client.post(f"/sessions/{sid}/esign", json={"form_id": "fssai_form_a"}, headers=headers)).status_code == 503


def test_prod_config_requires_webhook_secret_when_digio_is_configured(monkeypatch):
    from app.core.config import Settings, production_problems

    s = Settings(digio_client_id="a", digio_client_secret="b", digio_webhook_secret="")
    assert any("DIGIO_WEBHOOK_SECRET" in p for p in production_problems(s))
    assert not any("DIGIO" in p for p in production_problems(Settings(digio_client_id="a", digio_client_secret="b", digio_webhook_secret="x")))
    assert not any("DIGIO" in p for p in production_problems(Settings()))  # no Digio configured: nothing required


# ---------------- retry policy ----------------


@pytest.mark.asyncio
async def test_read_only_calls_retry_once_on_5xx_and_network_errors():
    calls = []

    def flaky(req: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(502)
        return httpx.Response(200, json={"agreement_status": "completed"})

    res = await DigioESign(digio_client(flaky)).get_status("DID1")
    assert res.ok and res.data["status"] == "completed" and len(calls) == 2

    calls.clear()

    def down(req: httpx.Request) -> httpx.Response:
        calls.append(1)
        raise httpx.ConnectError("down")

    res = await DigioESign(digio_client(down)).get_status("DID1")
    assert not res.ok and res.data["error"] == "provider_unreachable" and len(calls) == 2


@pytest.mark.asyncio
async def test_create_is_never_retried_so_a_signature_request_is_not_duplicated():
    calls = []

    def always_500(req: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(500, json={"code": "1001"})

    res = await DigioESign(digio_client(always_500)).create_request(PDF, "f.pdf", "a@b.in", "reason", "ref1")
    assert not res.ok and len(calls) == 1
