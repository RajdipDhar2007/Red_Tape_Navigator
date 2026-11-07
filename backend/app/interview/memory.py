"""Session memory: Postgres is the source of truth (sensitive values Fernet-encrypted), Redis caches non-sensitive."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import crypto
from app.core.cache import get_cache
from app.db.models import Answer, NavSession
from app.interview.fields import DERIVED, FIELDS


class AnswerError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _ck(session_id: str) -> str:
    return f"answers:{session_id}"


async def _rows(db: AsyncSession, session_id: str) -> list[Answer]:
    return list((await db.execute(select(Answer).where(Answer.session_id == session_id))).scalars())


async def get_answers(db: AsyncSession, session_id: str, *, reveal: bool = False) -> dict[str, dict]:
    """key -> {value, source, sensitive}. Sensitive values are masked unless `reveal` (form filling only)."""
    if not reveal:
        cached = await get_cache().get(_ck(session_id))
        if cached is not None:
            return cached
    out: dict[str, dict] = {}
    for r in await _rows(db, session_id):
        val = crypto.decrypt(r.value) if r.sensitive else r.value
        out[r.key] = {"value": val if (reveal or not r.sensitive) else crypto.mask(val), "source": r.source, "sensitive": r.sensitive}
    if not reveal:  # cache holds only the masked view, never plaintext Aadhaar/PAN
        await get_cache().set(_ck(session_id), out, ttl=900)
    return out


async def set_answer(db: AsyncSession, session_id: str, key: str, raw: str, source: str = "user") -> str:
    """Validate, normalise and upsert. Re-answering the same key edits it (a key is never stored twice)."""
    if key in DERIVED:
        value = raw.strip()[:200]
        sensitive = False
    else:
        fdef = FIELDS.get(key)
        if fdef is None:
            raise AnswerError("unknown_field")
        try:
            value = fdef.validate(raw)
        except ValueError as exc:
            raise AnswerError(str(exc)) from exc
        sensitive = fdef.sensitive
    stored = crypto.encrypt(value) if sensitive else value
    existing = (await db.execute(select(Answer).where(Answer.session_id == session_id, Answer.key == key))).scalar_one_or_none()
    if existing:
        existing.value, existing.sensitive, existing.source = stored, sensitive, source
    else:
        db.add(Answer(session_id=session_id, key=key, value=stored, sensitive=sensitive, source=source))
    ns = await db.get(NavSession, session_id)
    if ns and key in (ns.skipped or []):
        ns.skipped = [k for k in ns.skipped if k != key]
    if ns and ns.reviewed_at:  # any edit invalidates a previous review: the citizen must re-review
        ns.reviewed_at = None
    await db.commit()
    await get_cache().delete(_ck(session_id))
    return value


async def seed_derived(db: AsyncSession, ns: NavSession) -> None:
    p = ns.parsed or {}
    for k, v in (("city", p.get("city")), ("state", p.get("state")), ("business_type", p.get("activity"))):
        if v:
            await set_answer(db, ns.id, k, str(v), source="derived")


async def skip(db: AsyncSession, ns: NavSession, key: str) -> None:
    if key not in FIELDS:
        raise AnswerError("unknown_field")
    if key not in (ns.skipped or []):
        ns.skipped = [*(ns.skipped or []), key]
        await db.commit()


async def delete_answer(db: AsyncSession, session_id: str, key: str) -> None:
    for r in await _rows(db, session_id):
        if r.key == key:
            await db.delete(r)
    await db.commit()
    await get_cache().delete(_ck(session_id))
