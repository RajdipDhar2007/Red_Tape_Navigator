"""Re-encrypt all sensitive answers with the primary FIELD_ENCRYPTION_KEY.

Procedure (see docs/RUNBOOK.md):
  1. Generate a new key:            make keygen
  2. Set FIELD_ENCRYPTION_KEY="<new>,<old>"  (new first) and deploy - old data still decrypts.
  3. Run:                           python scripts/rotate_encryption_key.py
  4. Remove the old key from FIELD_ENCRYPTION_KEY and redeploy.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import select  # noqa: E402

from app.core.crypto import rotate  # noqa: E402
from app.db.models import Answer  # noqa: E402
from app.db.session import maker  # noqa: E402


async def main() -> int:
    n = 0
    async with maker()() as db:
        for a in (await db.execute(select(Answer).where(Answer.sensitive.is_(True)))).scalars():
            a.value = rotate(a.value)
            n += 1
        await db.commit()
    print(f"re-encrypted {n} values")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
