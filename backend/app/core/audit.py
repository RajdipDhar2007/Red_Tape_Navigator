"""Immutable, hash-chained audit log. Details are redacted before storage."""
import asyncio
import hashlib
import json
from datetime import UTC, datetime
from weakref import WeakKeyDictionary

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import redact
from app.db.models import AuditLog

GENESIS = "0" * 64
_AUDIT_ADVISORY_LOCK_ID = 748291041
_audit_locks: WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Lock] = WeakKeyDictionary()


def _get_audit_lock() -> asyncio.Lock:
    loop = asyncio.get_running_loop()
    lock = _audit_locks.get(loop)
    if lock is None:
        lock = asyncio.Lock()
        _audit_locks[loop] = lock
    return lock


def _digest(prev: str, ts: str, actor: str, action: str, session_id: str | None, detail: dict) -> str:
    body = json.dumps([prev, ts, actor, action, session_id, detail], sort_keys=True, default=str)
    return hashlib.sha256(body.encode()).hexdigest()


async def record(
    db: AsyncSession, actor: str, action: str, detail: dict | None = None, session_id: str | None = None
) -> AuditLog:
    async with _get_audit_lock():
        conn = await db.connection()
        stmt = select(AuditLog).order_by(AuditLog.seq.desc()).limit(1).execution_options(populate_existing=True)
        if conn.dialect.name == "postgresql":
            # Transaction-level advisory lock serializes chain appends across multiple workers even when audit_log is empty.
            await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": _AUDIT_ADVISORY_LOCK_ID})
            stmt = stmt.with_for_update()
        last = (await db.execute(stmt)).scalar_one_or_none()
        prev = last.hash if last else GENESIS
        ts = datetime.now(UTC)
        clean = redact(detail or {})
        row = AuditLog(
            ts=ts,
            actor=actor,
            action=action,
            session_id=session_id,
            detail=clean,
            prev_hash=prev,
            hash=_digest(prev, ts.isoformat(), actor, action, session_id, clean),
        )
        db.add(row)
        await db.commit()
        return row


async def verify_chain(db: AsyncSession) -> bool:
    rows = (await db.execute(select(AuditLog).order_by(AuditLog.seq))).scalars().all()
    prev = GENESIS
    for r in rows:
        ts = r.ts if r.ts.tzinfo else r.ts.replace(tzinfo=UTC)
        if r.prev_hash != prev or r.hash != _digest(prev, ts.isoformat(), r.actor, r.action, r.session_id, r.detail):
            return False
        prev = r.hash
    return True
