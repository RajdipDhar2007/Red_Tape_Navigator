"""First officer account from the environment, for hosts where no shell is available (e.g. a free hosting tier).

Set BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD (12+ characters), start the service once, sign in, change the
password in the app, then delete both variables. An existing account is only promoted: its password is never
overwritten here, so leaving the variables set cannot be used to take an account back over.
"""
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import audit
from app.core.config import Settings
from app.core.security import hash_password
from app.db.models import User


async def ensure_admin(db: AsyncSession, s: Settings) -> str:
    """Returns "created", "promoted", "unchanged" or "skipped"."""
    email, password = s.bootstrap_admin_email.strip().lower(), s.bootstrap_admin_password
    if not email or len(password) < 12:
        return "skipped"
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None:
        user = User(email=email, password_hash=await asyncio.to_thread(hash_password, password), role="admin")
        db.add(user)
        outcome = "created"
    elif user.role != "admin" and not user.deleted_at:
        user.role = "admin"
        outcome = "promoted"
    else:
        return "unchanged"
    await db.commit()
    await audit.record(db, user.id, "admin.bootstrap", {"role": "admin", "via": "env", "outcome": outcome})
    return outcome
