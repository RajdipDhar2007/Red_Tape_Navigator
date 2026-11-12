import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite+aiosqlite:///{_tmp}/test.db".replace("\\", "/")
os.environ["STORAGE_LOCAL_DIR"] = f"{_tmp}/vault".replace("\\", "/")
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
        if conn.dialect.name == "postgresql":
            await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    from app.core.middleware import limiter

    limiter.hits.clear()
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    await reset_engine()


@pytest.fixture
async def auth(client):
    r = await client.post("/auth/register", json={"email": "a@example.com", "password": "correct-horse-battery"})
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['access_token']}"}, r.json()
