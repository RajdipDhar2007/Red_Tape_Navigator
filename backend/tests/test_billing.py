import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import update

from app.billing import plans, providers, service
from app.core import config
from app.db.models import Subscription, User
from app.db.session import maker


@pytest.fixture
def billing_on(monkeypatch):
    for k, v in {"BILLING_ENABLED": "true", "BILLING_PROVIDER": "mock", "COMPANY_NAME": "Test Co", "COMPANY_ADDRESS": "Kolkata",
                 "RAZORPAY_WEBHOOK_SECRET": "whsec_test"}.items():
        monkeypatch.setenv(k, v)
    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


def test_pricing_file_is_marked_placeholder_and_complete():
    assert plans.load_pricing()["placeholder"] is True
    assert set(plans.plans()) == {"free", "plus", "multi", "partner"}
    assert plans.price_paise("plus", "month") == 19900 and plans.price_paise("free", "year") == 0
    with pytest.raises(ValueError):
        plans.price_paise("plus", "week")


def test_gst_split_and_effective_plan_grace():
    assert service.split_gst(19900, 18) == (19900, 3582, 23482)
    now = datetime.now(UTC)
    sub = Subscription(user_id="u", plan="plus", current_period_end=now - timedelta(days=3))
    assert service.effective_plan(sub, now) == ("plus", "grace")
    sub.current_period_end = now - timedelta(days=30)
    assert service.effective_plan(sub, now) == ("free", "free")
    sub.current_period_end = now + timedelta(days=1)
    assert service.effective_plan(sub, now) == ("plus", "active")


async def test_billing_off_opens_everything(client, auth):
    h, _ = auth
    me = (await client.get("/billing/me", headers=h)).json()
    assert me["state"] == "billing_off" and "form_prefill" in me["features"]
    assert (await client.post("/billing/checkout", json={"plan": "plus"}, headers=h)).status_code == 409
    assert (await client.get("/billing/plans")).json()["billing_enabled"] is False


async def test_free_plan_blocks_paid_feature_then_mock_payment_unlocks_it(client, auth, billing_on):
    h, _ = auth
    me = (await client.get("/billing/me", headers=h)).json()
    assert me["plan"] == "free" and "form_prefill" not in me["features"]
    assert (await client.post("/billing/checkout", json={"plan": "free"}, headers=h)).status_code == 422
    assert (await client.post("/billing/checkout", json={"plan": "plus", "interval": "week"}, headers=h)).status_code == 422
    co = (await client.post("/billing/checkout", json={"plan": "plus", "interval": "month"}, headers=h)).json()
    assert co["amount_paise"] == 23482 and "mock_order" in co["checkout_url"]
    assert (await client.get("/billing/me", headers=h)).json()["plan"] == "free"  # not granted until paid
    inv = (await client.post(f"/billing/mock/pay/{co['order_id']}", headers=h)).json()
    assert inv["number"].startswith("RTN-") and inv["number"].endswith("000001")
    assert inv["taxable_paise"] == 19900 and inv["gst_paise"] == 3582 and inv["total_paise"] == 23482
    again = (await client.post(f"/billing/mock/pay/{co['order_id']}", headers=h)).json()
    assert again["number"] == inv["number"]  # idempotent: no second invoice
    me = (await client.get("/billing/me", headers=h)).json()
    assert me["plan"] == "plus" and "form_prefill" in me["features"]
    assert len((await client.get("/billing/invoices", headers=h)).json()) == 1
    cancelled = (await client.post("/billing/cancel", headers=h)).json()
    assert cancelled["cancel_at_period_end"] is True and cancelled["plan"] == "plus"


async def test_mock_pay_is_scoped_to_the_owner_and_hidden_in_prod(client, auth, billing_on, monkeypatch):
    h, _ = auth
    co = (await client.post("/billing/checkout", json={"plan": "plus"}, headers=h)).json()
    other = await client.post("/auth/register", json={"email": "b@example.com", "password": "correct-horse-battery"})
    h2 = {"Authorization": f"Bearer {other.json()['access_token']}"}
    assert (await client.post(f"/billing/mock/pay/{co['order_id']}", headers=h2)).status_code == 404
    monkeypatch.setattr("app.api.billing.get_settings", lambda: type("S", (), {"is_prod": True, "billing_provider": "mock"})())
    assert (await client.post(f"/billing/mock/pay/{co['order_id']}", headers=h)).status_code == 404


async def test_require_feature_dependency_gates_on_the_plan(client, auth, billing_on):
    from fastapi import HTTPException

    h, _ = auth
    async with maker()() as db:
        user = await db.get(User, (await client.get("/auth/me", headers=h)).json()["id"])
        dep = service.require_feature("form_prefill")
        with pytest.raises(HTTPException) as exc:
            await dep(user=user, db=db)
        assert exc.value.status_code == 402 and exc.value.detail["feature"] == "form_prefill"
        assert "plan" in (await service.entitlements(db, user.id))


def _sign(body: bytes, secret="whsec_test"):
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _paid_event(order_id: str, amount: int) -> bytes:
    return json.dumps({"event": "payment_link.paid", "payload": {"payment_link": {"entity": {"reference_id": order_id, "amount_paid": amount}}}}).encode()


async def test_razorpay_webhook_signature_idempotency_and_amount_check(client, auth, billing_on):
    h, _ = auth
    co = (await client.post("/billing/checkout", json={"plan": "plus"}, headers=h)).json()
    body = _paid_event(co["order_id"], co["amount_paise"])
    bad = await client.post("/webhooks/razorpay", content=body, headers={"x-razorpay-signature": "0" * 64, "x-razorpay-event-id": "e1"})
    assert bad.status_code == 400
    ok_h = {"x-razorpay-signature": _sign(body), "x-razorpay-event-id": "e1"}
    assert (await client.post("/webhooks/razorpay", content=body, headers=ok_h)).json()["status"] == "ok"
    assert (await client.post("/webhooks/razorpay", content=body, headers=ok_h)).json()["status"] == "duplicate"
    assert (await client.get("/billing/me", headers=h)).json()["plan"] == "plus"
    assert len((await client.get("/billing/invoices", headers=h)).json()) == 1
    co2 = (await client.post("/billing/checkout", json={"plan": "multi"}, headers=h)).json()
    short = _paid_event(co2["order_id"], 100)
    r = await client.post("/webhooks/razorpay", content=short, headers={"x-razorpay-signature": _sign(short), "x-razorpay-event-id": "e2"})
    assert r.status_code == 200
    assert (await client.get("/billing/me", headers=h)).json()["plan"] == "plus"  # underpaid order was not settled
    missing = await client.post("/webhooks/razorpay", content=body, headers={"x-razorpay-signature": _sign(body)})
    assert missing.status_code == 400


async def test_admin_can_record_a_refund_and_plan_drops(client, auth, billing_on):
    h, _ = auth
    co = (await client.post("/billing/checkout", json={"plan": "plus"}, headers=h)).json()
    inv = (await client.post(f"/billing/mock/pay/{co['order_id']}", headers=h)).json()
    assert (await client.post(f"/billing/admin/refund/{inv['number']}", headers=h)).status_code == 403
    async with maker()() as db:
        uid = (await client.get("/auth/me", headers=h)).json()["id"]
        await db.execute(update(User).where(User.id == uid).values(role="admin"))
        await db.commit()
    r = await client.post(f"/billing/admin/refund/{inv['number']}", headers=h)
    assert r.json()["status"] == "refunded"
    assert (await client.get("/billing/me", headers=h)).json()["plan"] == "free"
    assert (await client.post("/billing/admin/refund/NOPE", headers=h)).status_code == 404


async def test_razorpay_adapter_request_shape_and_errors():
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["body"], seen["auth"] = json.loads(req.content), req.headers.get("authorization")
        return httpx.Response(200, json={"id": "plink_1", "short_url": "https://rzp.io/i/abc"})

    p = providers.RazorpayProvider("rzp_test_x", "secret", httpx.MockTransport(handler))
    co = await p.create_checkout("ord1", 23482, "Plus", "a@example.com", "https://x/billing")
    assert co.ok and co.url == "https://rzp.io/i/abc" and co.provider_ref == "plink_1"
    assert seen["body"]["amount"] == 23482 and seen["body"]["reference_id"] == "ord1" and seen["body"]["currency"] == "INR"
    assert seen["auth"].startswith("Basic ")
    bad = providers.RazorpayProvider("k", "s", httpx.MockTransport(lambda r: httpx.Response(400, json={"error": {}})))
    assert not (await bad.create_checkout("o", 1, "d", "e", "u")).ok

    def boom(req):
        raise httpx.ConnectError("down")

    down = providers.RazorpayProvider("k", "s", httpx.MockTransport(boom))
    assert "unreachable" in (await down.create_checkout("o", 1, "d", "e", "u")).error
    assert providers.verify_razorpay_signature("s", b"x", hmac.new(b"s", b"x", hashlib.sha256).hexdigest())
    assert not providers.verify_razorpay_signature("s", b"x", "")


def test_prod_requires_billing_settings():
    probs = config.production_problems(config.Settings(billing_enabled=True, billing_provider="mock"))
    assert any("BILLING_PROVIDER" in p for p in probs)
    probs = config.production_problems(config.Settings(billing_enabled=True, billing_provider="razorpay"))
    assert any("RAZORPAY" in p for p in probs) and any("COMPANY_NAME" in p for p in probs)


async def test_form_download_is_a_paid_feature_enforced_on_the_server(client, auth, monkeypatch):
    from tests.test_api_flow import ANSWERS, start

    headers, s = await start(client, auth)
    sid = s["id"]
    await client.post(f"/sessions/{sid}/research", json={}, headers=headers)
    for _ in range(40):
        st = (await client.get(f"/sessions/{sid}/interview", headers=headers)).json()
        if not st["questions"]:
            break
        await client.post(f"/sessions/{sid}/interview", json={"answers": {q["key"]: ANSWERS[q["key"]] for q in st["questions"]}}, headers=headers)
    assert (await client.post(f"/sessions/{sid}/review", json={"confirm": True}, headers=headers)).status_code == 200
    url = f"/sessions/{sid}/forms/fssai_form_a/download"
    assert (await client.get(url, headers=headers)).status_code == 200  # billing off: open
    for k, v in {"BILLING_ENABLED": "true", "COMPANY_NAME": "T", "COMPANY_ADDRESS": "K"}.items():
        monkeypatch.setenv(k, v)
    config.get_settings.cache_clear()
    try:
        r = await client.get(url, headers=headers)
        assert r.status_code == 402 and r.json()["detail"]["feature"] == "form_prefill"
    finally:
        config.get_settings.cache_clear()


async def test_invoice_pdf_is_owner_only_and_marked_draft_without_gstin(client, auth, billing_on):
    h, _ = auth
    co = (await client.post("/billing/checkout", json={"plan": "plus"}, headers=h)).json()
    inv = (await client.post(f"/billing/mock/pay/{co['order_id']}", headers=h)).json()
    r = await client.get(f"/billing/invoices/{inv['number']}/pdf", headers=h)
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    import pymupdf

    text = "".join(p.get_text() for p in pymupdf.open(stream=r.content, filetype="pdf"))
    assert inv["number"] in text and "DRAFT" in text and "Rs 234.82" in text
    other = await client.post("/auth/register", json={"email": "c@example.com", "password": "correct-horse-battery"})
    h2 = {"Authorization": f"Bearer {other.json()['access_token']}"}
    assert (await client.get(f"/billing/invoices/{inv['number']}/pdf", headers=h2)).status_code == 404
