"""Entitlements, order settlement and invoices. All enforcement is server-side."""
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.billing import plans
from app.core.config import get_settings
from app.db.models import BillingOrder, Invoice, Subscription, User
from app.db.session import get_db


def _aware(d: datetime | None) -> datetime | None:
    return d.replace(tzinfo=UTC) if d is not None and d.tzinfo is None else d  # SQLite returns naive datetimes


def effective_plan(sub: Subscription | None, now: datetime | None = None) -> tuple[str, str]:
    """(plan id, state). State is active | grace | free. A paid plan keeps working for the grace period after it lapses."""
    now = now or datetime.now(UTC)
    if sub is None or sub.plan == "free":
        return "free", "free"
    end = _aware(sub.current_period_end)
    if end is None or now <= end:
        return sub.plan, "active"
    if now <= end + timedelta(days=plans.grace_days()):
        return sub.plan, "grace"
    return "free", "free"


async def entitlements(db: AsyncSession, user_id: str) -> dict:
    if not get_settings().billing_enabled:  # billing off: everything is open, nothing is charged
        every = set().union(*(set(p["features"]) for p in plans.plans().values()))
        return {"plan": "all", "state": "billing_off", "features": sorted(every), "limits": {}, "billing_enabled": False}
    sub = await db.get(Subscription, user_id)
    plan, state = effective_plan(sub)
    end = _aware(sub.current_period_end) if sub else None
    return {"plan": plan, "state": state, "features": sorted(plans.features_of(plan)), "limits": plans.limits_of(plan),
            "billing_enabled": True, "current_period_end": end.isoformat() if end else None,
            "cancel_at_period_end": bool(sub and sub.cancel_at_period_end)}


def require_feature(feature: str):
    """FastAPI dependency: 402 unless the caller's plan includes ``feature``. Never trust the UI to hide things."""
    async def dep(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> User:
        ent = await entitlements(db, user.id)
        if feature not in ent["features"]:
            raise HTTPException(402, {"error": "upgrade_required", "feature": feature, "plan": ent["plan"]})
        return user

    return dep


def split_gst(total_excl_gst_paise: int, percent: int) -> tuple[int, int, int]:
    gst = (total_excl_gst_paise * percent + 50) // 100  # round half up to the paisa
    return total_excl_gst_paise, gst, total_excl_gst_paise + gst


async def _next_seq(db: AsyncSession) -> int:
    return int((await db.execute(select(func.coalesce(func.max(Invoice.seq), 0)))).scalar_one()) + 1


async def settle_order(db: AsyncSession, order: BillingOrder) -> Invoice | None:
    """Mark an order paid, extend the subscription and issue the invoice. Idempotent: a paid order returns its invoice unchanged."""
    existing = (await db.execute(select(Invoice).where(Invoice.order_id == order.id))).scalar_one_or_none()
    if existing is not None:
        return existing
    s = get_settings()
    now = datetime.now(UTC)
    order.status = "paid"
    sub = await db.get(Subscription, order.user_id)
    days = 365 if order.interval == "year" else 30
    if sub is None:
        sub = Subscription(user_id=order.user_id)
        db.add(sub)
    start = now
    cur_end = _aware(sub.current_period_end)
    if sub.plan == order.plan and cur_end and cur_end > now:  # renewing the same plan stacks onto the remaining time
        start = cur_end
    sub.plan, sub.interval, sub.status, sub.cancel_at_period_end = order.plan, order.interval, "active", False
    sub.current_period_end, sub.updated_at = start + timedelta(days=days), now
    total = order.amount_paise  # what the customer paid, GST included
    taxable = (total * 100 + (100 + s.invoice_gst_percent) // 2) // (100 + s.invoice_gst_percent)
    gst = total - taxable
    for _ in range(5):  # another settlement may take the same number; the unique constraint decides, we retry
        seq = await _next_seq(db)
        inv = Invoice(seq=seq, number=f"{s.invoice_prefix}-{now.year}-{seq:06d}", order_id=order.id, user_id=order.user_id,
                      description=f"{plans.plans()[order.plan]['name']} plan, 1 {order.interval}", taxable_paise=taxable,
                      gst_paise=gst, total_paise=total, gst_percent=s.invoice_gst_percent)
        try:
            async with db.begin_nested():
                db.add(inv)
                await db.flush()
            return inv
        except IntegrityError:
            continue
    return None
