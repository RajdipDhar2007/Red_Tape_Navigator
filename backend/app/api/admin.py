"""Human escalation (review queue for CSC operators / officers) and admin operations."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.llm import LLM
from app.agent.research import refresh_all
from app.api.deps import require_roles
from app.core import audit
from app.db.models import Claim, ReviewItem, User
from app.db.session import get_db
from app.services import privacy

router = APIRouter(prefix="/admin", tags=["admin"])
STAFF = ("csc_operator", "reviewer", "admin")


class ResolveIn(BaseModel):
    status: str = Field(pattern="^(verified|corrected|rejected)$")
    resolution: str = Field(min_length=3, max_length=1000)


@router.get("/review-queue")
async def queue(status: str = "open", user: User = Depends(require_roles(*STAFF)), db: AsyncSession = Depends(get_db)):
    items = (await db.execute(select(ReviewItem).where(ReviewItem.status == status).order_by(ReviewItem.created_at))).scalars().all()
    out = []
    for i in items:
        c = await db.get(Claim, i.claim_id) if i.claim_id else None
        out.append({
            "id": i.id, "reason": i.reason, "session_id": i.session_id, "status": i.status,
            "claim": {"key": c.key, "text": c.text, "source_url": c.source_url, "confidence": c.confidence, "fetched_at": c.fetched_at.isoformat()} if c else None,
        })
    return out


@router.post("/review-queue/{item_id}/resolve")
async def resolve(item_id: str, body: ResolveIn, user: User = Depends(require_roles(*STAFF)), db: AsyncSession = Depends(get_db)):
    item = await db.get(ReviewItem, item_id)
    if item is None:
        raise HTTPException(404, "Not found")
    item.status, item.resolution = body.status, body.resolution
    if body.status == "verified" and item.claim_id:
        c = await db.get(Claim, item.claim_id)
        if c:
            c.needs_verification = False
            c.confidence = max(c.confidence, 0.9)  # human-verified
    await db.commit()
    await audit.record(db, user.id, "review_queue.resolved", {"item": item_id, "status": body.status})
    return {"id": item.id, "status": item.status}


@router.post("/refresh")
async def refresh(user: User = Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    res = await refresh_all(db, llm=LLM())
    await audit.record(db, user.id, "admin.refresh", {"fetched": res["fetched"], "changed": len(res["changed_sources"])})
    return res


@router.post("/purge")
async def purge(user: User = Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    return {"purged_sessions": await privacy.purge_expired(db)}


@router.get("/audit/verify")
async def verify_audit(user: User = Depends(require_roles("admin", "reviewer")), db: AsyncSession = Depends(get_db)):
    return {"chain_valid": await audit.verify_chain(db)}


@router.post("/users/{user_id}/role")
async def set_role(user_id: str, role: str, user: User = Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    from app.core.security import ROLES

    if role not in ROLES:
        raise HTTPException(422, "Unknown role")
    target = await db.get(User, user_id)
    if target is None:
        raise HTTPException(404, "Not found")
    target.role = role
    await db.commit()
    await audit.record(db, user.id, "admin.role_changed", {"target": user_id, "role": role})
    return {"id": target.id, "role": target.role}
