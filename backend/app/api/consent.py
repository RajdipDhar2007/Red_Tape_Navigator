"""DPDP Act 2023: notice, consent log, withdrawal."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.core import audit
from app.db.models import Consent, User
from app.db.session import get_db

router = APIRouter(prefix="/consent", tags=["consent"])
POLICY_VERSION = "1.0"
PURPOSES = {
    "service": "To research regulations, ask for missing details and fill government forms on your behalf.",
    "identity_providers": "To share the form you reviewed with our signing partner (Digio) so you can sign it with Aadhaar, and to fetch documents you approve from DigiLocker. You approve each step on the partner page.",
    "reminders": "To send you renewal and follow-up reminders (email / WhatsApp / SMS).",
}


class ConsentIn(BaseModel):
    purpose: str
    granted: bool


@router.get("/notice")
async def notice():
    return {
        "policy_version": POLICY_VERSION,
        "purposes": PURPOSES,
        "data_collected": "Only the details required by the forms you choose. Aadhaar/PAN are encrypted at rest.",
        "retention": "Session data is deleted automatically after the retention period.",
        "rights": ["access/export", "correction", "erasure", "withdraw consent", "grievance redressal"],
        "disclaimer": "AI-assisted guidance, not legal advice. Verify with the issuing authority.",
    }


@router.post("", status_code=201)
async def give(body: ConsentIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    if body.purpose not in PURPOSES:
        from fastapi import HTTPException

        raise HTTPException(422, "Unknown purpose")
    db.add(Consent(user_id=user.id, purpose=body.purpose, policy_version=POLICY_VERSION, granted=body.granted))
    await db.commit()
    await audit.record(db, user.id, "consent.granted" if body.granted else "consent.withdrawn", {"purpose": body.purpose})
    return {"purpose": body.purpose, "granted": body.granted, "policy_version": POLICY_VERSION}


async def has_consent(db: AsyncSession, user_id: str, purpose: str) -> bool:
    rows = (
        await db.execute(
            select(Consent).where(Consent.user_id == user_id, Consent.purpose == purpose).order_by(Consent.created_at.desc())
        )
    ).scalars().all()
    return bool(rows and rows[0].granted)


@router.get("")
async def log(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Consent).where(Consent.user_id == user.id).order_by(Consent.created_at))).scalars()
    return [
        {"purpose": r.purpose, "granted": r.granted, "policy_version": r.policy_version, "at": r.created_at.isoformat()}
        for r in rows
    ]
