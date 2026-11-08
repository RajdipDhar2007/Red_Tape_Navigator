"""Create (or promote) the first admin / staff account. Run once per environment, on a trusted machine.

  ADMIN_PASSWORD='...' python scripts/create_admin.py officer@dept.gov.in [admin|reviewer|csc_operator]   # from backend/, or /app/scripts/ in the image

The password is read from the ADMIN_PASSWORD env var (never a CLI argument, so it stays out of shell history).
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ in the repo, /app in the image

from sqlalchemy import select  # noqa: E402

from app.core import audit  # noqa: E402
from app.core.security import ROLES, hash_password  # noqa: E402
from app.db.models import User  # noqa: E402
from app.db.session import maker  # noqa: E402


async def main(email: str, role: str, password: str) -> int:
    if role not in ROLES or role == "citizen":
        print(f"role must be one of {[r for r in ROLES if r != 'citizen']}")
        return 2
    if len(password) < 12:
        print("ADMIN_PASSWORD must be at least 12 characters")
        return 2
    async with maker()() as db:
        user = (await db.execute(select(User).where(User.email == email.lower()))).scalar_one_or_none()
        if user is None:
            user = User(email=email.lower(), password_hash=hash_password(password), role=role)
            db.add(user)
        else:
            user.role = role
            user.password_hash = hash_password(password)
            user.deleted_at = None
        await db.commit()
        await audit.record(db, user.id, "admin.bootstrap", {"role": role})
    print(f"{email} is now {role}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2 or not os.environ.get("ADMIN_PASSWORD"):
        print(__doc__)
        sys.exit(2)
    sys.exit(asyncio.run(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "admin", os.environ["ADMIN_PASSWORD"])))
