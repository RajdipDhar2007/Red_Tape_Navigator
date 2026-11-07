from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, consent
from app.core.config import get_settings
from app.db.models import Base
from app.db.session import get_engine

DISCLAIMER = "AI-assisted guidance, not legal advice. Verify with the issuing authority."


@asynccontextmanager
async def lifespan(_: FastAPI):
    if get_settings().database_url.startswith("sqlite"):  # dev/test convenience; prod uses Alembic
        async with get_engine().begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title="Red Tape Navigator", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "Accept-Language"],
    )
    app.include_router(auth.router)
    app.include_router(consent.router)

    @app.get("/health")
    async def health():
        return {"status": "ok", "disclaimer": DISCLAIMER}

    return app


app = create_app()
