import json

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.core import audit
from app.core.config import get_settings
from app.db.models import User
from app.db.session import get_db
from app.services import privacy
from app.services.session_service import get_owned

router = APIRouter(prefix="/privacy", tags=["privacy (DPDP)"])


@router.get("/export")
async def export(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await audit.record(db, user.id, "privacy.export")
    data = await privacy.export_user_data(db, user)
    return Response(
        json.dumps(data, ensure_ascii=False, indent=2), media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="my-data.json"'},
    )


@router.delete("/me")
async def erase_me(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return await privacy.erase_user(db, user)


@router.delete("/sessions/{sid}", status_code=204)
async def delete_session(sid: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    ns = await get_owned(db, user, sid)
    await privacy._delete_session_data(db, [ns.id])
    await db.commit()
    await audit.record(db, user.id, "privacy.session_deleted")
    return Response(status_code=204)


@router.get("/policy")
async def policy():
    s = get_settings()
    return {"retention_days": s.retention_days, "data_region": s.data_region, "grievance": "Contact the Data Protection Officer listed in docs/COMPLIANCE.md"}

