"""Orchestration helpers shared by the API: ownership, required fields, filling, tracker."""
import hashlib
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import NavSession, User, WorkspaceMember
from app.forms import filler, official
from app.forms.context import build_context
from app.forms.registry import get_template, required_keys_for
from app.interview import engine, memory

STAGES = ["goal", "research", "checklist", "interview", "review", "submit"]
PRIVILEGED = {"admin", "reviewer"}


async def get_owned(db: AsyncSession, user: User, sid: str) -> NavSession:
    ns = await db.get(NavSession, sid)
    if ns is None:
        raise HTTPException(404, "Session not found")
    allowed = ns.user_id == user.id or user.role in PRIVILEGED
    if not allowed and ns.workspace_id:  # shared into a team the caller belongs to
        allowed = await db.get(WorkspaceMember, (ns.workspace_id, user.id)) is not None
    if not allowed:
        raise HTTPException(404, "Session not found")  # 404 not 403: do not reveal existence
    return ns


def new_session(user: User, goal: str, language: str) -> NavSession:
    exp = datetime.now(UTC) + timedelta(days=get_settings().retention_days)
    return NavSession(user_id=user.id, goal=goal[:1000], language=language, expires_at=exp)


def form_ids(ns: NavSession) -> list[str]:
    seen: list[str] = []
    for s in (ns.plan or {}).get("steps", []):
        if s.get("form") and s["form"] not in seen:
            seen.append(s["form"])
    return seen


def required_keys(ns: NavSession) -> set[str]:
    return required_keys_for(form_ids(ns))


async def fill_all(db: AsyncSession, ns: NavSession) -> dict[str, filler.FillResult]:
    answers = await memory.get_answers(db, ns.id, reveal=True)
    values = filler.build_values(answers, build_context(ns.parsed or {}))
    out = {}
    for fid in form_ids(ns):
        src = await official.active_source(db, fid)
        out[fid] = filler.fill_form(get_template(fid), values, src.pdf if src else None, official=src is not None)
    return out


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


async def tracker(db: AsyncSession, ns: NavSession) -> dict:
    has_plan = bool((ns.plan or {}).get("steps"))
    if not ns.parsed or ns.parsed.get("clarifying_question"):
        current = "goal"
    elif not has_plan:
        current = "research"
    elif ns.reviewed_at:
        current = "submit"
    else:
        st = await engine.state(db, ns, required_keys(ns))
        started = st["progress"]["answered"] > 0
        current = "review" if (st["ready_for_review"] and started) else "interview" if started else "checklist"
    idx = STAGES.index(current)
    return {"current": current, "steps": [{"id": s, "done": i < idx, "active": i == idx} for i, s in enumerate(STAGES)]}
