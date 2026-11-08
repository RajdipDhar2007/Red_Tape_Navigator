import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.consent import has_consent
from app.db.models import Reminder
from app.followup.checklist import RENEWAL_MONTHS
from app.integrations.interfaces import Integrations
from app.kb.catalog import LICENCES

log = logging.getLogger(__name__)


async def schedule_after_submission(
    db: AsyncSession, *, session_id: str, user_id: str, licences: list[str], channel: str, destination: str, now: datetime | None = None
) -> list[Reminder]:
    """Called when the CITIZEN says they submitted. Creates a status-check and a renewal reminder per licence."""
    now = now or datetime.now(UTC)
    created = []
    for lid in licences:
        name = LICENCES[lid]["name"]
        created.append(Reminder(session_id=session_id, user_id=user_id, kind="status", title=f"Check status of your {name} application", due_at=now + timedelta(days=14), channel=channel, destination=destination))
        months = RENEWAL_MONTHS.get(lid)
        if months:
            created.append(Reminder(session_id=session_id, user_id=user_id, kind="renewal", title=f"Renewal check for {name} (verify the exact due date on your certificate)", due_at=now + timedelta(days=int(months * 30.4) - 30), channel=channel, destination=destination))
    db.add_all(created)
    await db.commit()
    return created


async def dispatch_due(db: AsyncSession, integrations: Integrations, now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    rows = (await db.execute(select(Reminder).where(Reminder.sent.is_(False)))).scalars().all()
    sent = 0
    for r in rows:
        due = r.due_at if r.due_at.tzinfo else r.due_at.replace(tzinfo=UTC)
        if due > now:
            continue
        m = integrations.messengers.get(r.channel)
        if m is None or not r.destination:
            continue
        if not await has_consent(db, r.user_id, "reminders"):  # consent withdrawn: never send
            r.sent = True  # close it out so it is not retried; nothing is delivered
            continue
        try:
            res = await m.send(r.destination, f"{r.title}. AI-assisted guidance, not legal advice. Verify with the issuing authority.")
        except Exception:  # noqa: BLE001 - e.g. a channel whose provider is not onboarded; keep the batch going
            log.exception("reminder channel %s failed", r.channel)
            continue
        if res.ok:
            r.sent = True
            sent += 1
    await db.commit()
    return sent
