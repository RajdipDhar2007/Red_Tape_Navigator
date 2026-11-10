"""Plans, checkout, subscription state, invoices, and the Razorpay webhook.

Card/UPI details never touch this server (hosted checkout). A plan is granted only when an order is settled, and an order is
settled only by a verified provider webhook (or the dev-only mock endpoint, which is disabled in production).
"""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user, require_roles
from app.billing import plans
from app.billing.providers import get_provider, verify_razorpay_signature
from app.billing.service import entitlements, settle_order, split_gst
from app.core import audit
from app.core.config import get_settings
from app.db.models import BillingOrder, Invoice, Subscription, User, WebhookEvent
from app.db.session import get_db

router = APIRouter(prefix="/billing", tags=["billing"])
hook = APIRouter(prefix="/webhooks", tags=["webhooks"])
log = logging.getLogger(__name__)
MAX_BODY = 200_000


class CheckoutIn(BaseModel):
    plan: str
    interval: str = "month"


def _invoice_json(i: Invoice) -> dict:
    s = get_settings()
    return {"number": i.number, "issued_at": i.issued_at.isoformat(), "description": i.description, "taxable_paise": i.taxable_paise,
            "gst_percent": i.gst_percent, "gst_paise": i.gst_paise, "total_paise": i.total_paise, "status": i.status,
            "seller": {"name": s.company_name, "address": s.company_address, "gstin": s.company_gstin, "sac": s.invoice_sac_code}}


@router.get("/plans")
async def list_plans():
    s = get_settings()
    return {"billing_enabled": s.billing_enabled, "gst_percent": s.invoice_gst_percent, "plans": plans.public_plans()}


@router.get("/me")
async def my_billing(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return await entitlements(db, user.id)


@router.post("/checkout", status_code=201)
async def checkout(body: CheckoutIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    s = get_settings()
    if not s.billing_enabled:
        raise HTTPException(409, "Billing is not enabled")
    if body.plan == "free" or body.plan not in plans.plans() or body.interval not in plans.INTERVALS:
        raise HTTPException(422, "Unknown plan or interval")
    price = plans.price_paise(body.plan, body.interval)
    _, _, total = split_gst(price, s.invoice_gst_percent)
    provider = get_provider(s)
    order = BillingOrder(user_id=user.id, plan=body.plan, interval=body.interval, amount_paise=total, provider=provider.name)
    db.add(order)
    await db.flush()
    desc = f"Red Tape Navigator {plans.plans()[body.plan]['name']} plan, 1 {body.interval}"
    co = await provider.create_checkout(order.id, total, desc, user.email, f"{s.web_base_url.rstrip('/')}/billing")
    if not co.ok:
        await db.rollback()
        raise HTTPException(502, co.error or "Payment provider error")
    order.provider_ref = co.provider_ref
    await audit.record(db, user.id, "billing.checkout_started", detail={"plan": body.plan, "interval": body.interval})
    await db.commit()
    return {"order_id": order.id, "checkout_url": co.url, "amount_paise": total, "currency": "INR"}


@router.post("/cancel")
async def cancel(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    """Stops renewal reminders; the paid period stays usable until it ends. Nothing is auto-debited, so there is nothing to stop at the bank."""
    sub = await db.get(Subscription, user.id)
    if sub is None or sub.plan == "free":
        raise HTTPException(409, "No paid plan to cancel")
    sub.cancel_at_period_end = True
    await audit.record(db, user.id, "billing.cancel")
    await db.commit()
    return await entitlements(db, user.id)


@router.get("/invoices")
async def my_invoices(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Invoice).where(Invoice.user_id == user.id).order_by(Invoice.seq.desc()))).scalars().all()
    return [_invoice_json(i) for i in rows]


@router.post("/admin/refund/{number}")
async def record_refund(number: str, admin: User = Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    """Records that a refund was made at the provider (money is returned in the provider dashboard, not by this API)."""
    from datetime import UTC, datetime

    inv = (await db.execute(select(Invoice).where(Invoice.number == number))).scalar_one_or_none()
    if inv is None:
        raise HTTPException(404, "Unknown invoice")
    inv.status, inv.refunded_at = "refunded", datetime.now(UTC)
    sub = await db.get(Subscription, inv.user_id)
    if sub is not None:
        sub.plan, sub.current_period_end = "free", None
    await audit.record(db, admin.id, "billing.refund_recorded", detail={"invoice": number})
    await db.commit()
    return _invoice_json(inv)


@router.post("/mock/pay/{order_id}")
async def mock_pay(order_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    """Development/test only: settles a mock order as if the provider reported success. Disabled in production."""
    s = get_settings()
    if s.is_prod or s.billing_provider != "mock":
        raise HTTPException(404, "Not found")
    order = await db.get(BillingOrder, order_id)
    if order is None or order.user_id != user.id or order.provider != "mock":
        raise HTTPException(404, "Unknown order")
    inv = await settle_order(db, order)
    await audit.record(db, user.id, "billing.paid", detail={"order": order.id, "mock": True})
    await db.commit()
    return _invoice_json(inv) if inv else {}


@hook.post("/razorpay")
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    s = get_settings()
    body = await request.body()
    if len(body) > MAX_BODY:
        raise HTTPException(413, "Too large")
    if not s.razorpay_webhook_secret or not verify_razorpay_signature(s.razorpay_webhook_secret, body, request.headers.get("x-razorpay-signature", "")):
        raise HTTPException(400, "Invalid signature")
    event_id = request.headers.get("x-razorpay-event-id", "")
    try:
        payload = json.loads(body)
    except ValueError:
        return {"status": "ignored"}
    if not event_id:
        raise HTTPException(400, "Missing event id")
    try:  # at-least-once delivery: a repeated event id is acknowledged and not processed again
        async with db.begin_nested():
            db.add(WebhookEvent(id=f"rzp:{event_id}"[:64]))
            await db.flush()
    except IntegrityError:
        return {"status": "duplicate"}
    if payload.get("event") == "payment_link.paid":
        link = ((payload.get("payload") or {}).get("payment_link") or {}).get("entity") or {}
        order = await db.get(BillingOrder, str(link.get("reference_id", "")))
        if order is None:
            log.warning("razorpay paid event for unknown order")  # authentic but irrelevant: acknowledge so it is not retried
        elif int(link.get("amount_paid") or 0) != order.amount_paise:
            log.warning("razorpay paid amount differs from the order; not settled")
            await audit.record(db, order.user_id, "billing.amount_mismatch", detail={"order": order.id})
        else:
            await settle_order(db, order)
            await audit.record(db, order.user_id, "billing.paid", detail={"order": order.id})
    await db.commit()
    return {"status": "ok"}
