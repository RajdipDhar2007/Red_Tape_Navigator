"""DPDP Act 2023 data-principal rights: access/export, erasure, and automatic retention purge."""
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import audit
from app.core.cache import get_cache
from app.db.models import Answer, Consent, NavSession, RefreshToken, Reminder, ReviewItem, User
from app.interview import memory


async def export_user_data(db: AsyncSession, user: User) -> dict:
    sessions = (await db.execute(select(NavSession).where(NavSession.user_id == user.id))).scalars().all()
    out_sessions = []
    for s in sessions:
        ans = await memory.get_answers(db, s.id, reveal=True)  # the data principal may see their own data in full
        out_sessions.append({
            "id": s.id, "goal": s.goal, "language": s.language, "parsed": s.parsed, "created_at": s.created_at.isoformat(),
            "reviewed_at": s.reviewed_at.isoformat() if s.reviewed_at else None,
            "answers": {k: {"value": v["value"], "source": v["source"]} for k, v in ans.items()},
        })
    consents = (await db.execute(select(Consent).where(Consent.user_id == user.id).order_by(Consent.created_at))).scalars().all()
    reminders = (await db.execute(select(Reminder).where(Reminder.user_id == user.id))).scalars().all()
    return {
        "exported_at": datetime.now(UTC).isoformat(),
        "user": {"id": user.id, "email": user.email, "role": user.role, "language": user.language, "created_at": user.created_at.isoformat()},
        "consents": [{"purpose": c.purpose, "granted": c.granted, "policy_version": c.policy_version, "at": c.created_at.isoformat()} for c in consents],
        "sessions": out_sessions,
        "reminders": [{"title": r.title, "due_at": r.due_at.isoformat(), "channel": r.channel, "sent": r.sent} for r in reminders],
    }


async def _delete_session_data(db: AsyncSession, session_ids: list[str]) -> None:
    if not session_ids:
        return
    await db.execute(delete(Answer).where(Answer.session_id.in_(session_ids)))
    await db.execute(delete(Reminder).where(Reminder.session_id.in_(session_ids)))
    await db.execute(delete(ReviewItem).where(ReviewItem.session_id.in_(session_ids)))
    await db.execute(delete(NavSession).where(NavSession.id.in_(session_ids)))
    for sid in session_ids:
        await get_cache().delete(f"answers:{sid}")


async def erase_user(db: AsyncSession, user: User) -> dict:
    """Erase personal data. The consent log and (PII-free) audit entries are retained as legal records."""
    ids = list((await db.execute(select(NavSession.id).where(NavSession.user_id == user.id))).scalars())
    await _delete_session_data(db, ids)
    await db.execute(delete(RefreshToken).where(RefreshToken.user_id == user.id))
    user.email = f"deleted-{uuid.uuid4().hex[:12]}@erased.invalid"
    user.password_hash = "!"
    user.deleted_at = datetime.now(UTC)
    await db.commit()
    await audit.record(db, user.id, "privacy.erasure", {"sessions": len(ids)})
    return {"erased": True, "sessions_deleted": len(ids)}


async def purge_expired(db: AsyncSession, now: datetime | None = None) -> int:
    """Retention policy: sessions past `expires_at` are deleted automatically (scheduled job)."""
    now = now or datetime.now(UTC)
    rows = (await db.execute(select(NavSession).where(NavSession.expires_at.is_not(None)))).scalars().all()
    ids = [s.id for s in rows if (s.expires_at if s.expires_at.tzinfo else s.expires_at.replace(tzinfo=UTC)) < now]
    await _delete_session_data(db, ids)
    await db.commit()
    if ids:
        await audit.record(db, "system", "retention.purge", {"sessions": len(ids)})
    return len(ids)
