import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp}/test.db".replace("\\", "/")
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["APP_ENV"] = "test"

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.db.models import Base  # noqa: E402
from app.db.session import get_engine, reset_engine  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture
async def client():
    await reset_engine()
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    await reset_engine()


@pytest.fixture
async def auth(client):
    r = await client.post("/auth/register", json={"email": "a@example.com", "password": "correct-horse-battery"})
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['access_token']}"}, r.json()
