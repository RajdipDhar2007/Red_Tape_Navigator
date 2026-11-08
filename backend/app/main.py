import hmac
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy import func, select, text

from app.api import admin, auth, consent, privacy, sessions, webhooks
from app.core import metrics
from app.core.config import get_settings
from app.core.errors import capture_exception, init_error_tracking
from app.core.logging import configure_logging
from app.core.middleware import HardeningMiddleware
from app.core.tracing import configure_tracing
from app.db.models import Base, Claim
from app.db.session import get_engine, maker
from app.db.sqlite_upgrade import add_missing_columns

DISCLAIMER = "AI-assisted guidance, not legal advice. Verify with the issuing authority."


@asynccontextmanager
async def lifespan(_: FastAPI):
    s = get_settings()
    configure_logging(s.log_level)
    configure_tracing()
    init_error_tracking()
    if s.database_url.startswith("sqlite"):  # dev/test convenience; production uses Alembic (make migrate)
        async with get_engine().begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.run_sync(add_missing_columns)  # an old local .db file must not break login after an upgrade
    yield


def create_app() -> FastAPI:
    s = get_settings()
    # OpenAPI docs are disabled in production to reduce the attack surface
    app = FastAPI(
        title="Red Tape Navigator", version="0.1.0", lifespan=lifespan,
        docs_url=None if s.is_prod else "/docs", redoc_url=None, openapi_url=None if s.is_prod else "/openapi.json",
    )
    app.add_middleware(HardeningMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "Accept-Language", "X-Request-ID"],
        expose_headers=["X-Request-ID", "Content-Disposition"],
    )
    for r in (auth.router, consent.router, sessions.router, privacy.router, admin.router, webhooks.router):
        app.include_router(r)

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        capture_exception(exc, path=request.url.path)
        return JSONResponse({"detail": "Internal error"}, status_code=500)  # never leak internals

    @app.get("/health", tags=["ops"])
    async def health():
        """Liveness: the process is up."""
        return {"status": "ok", "disclaimer": DISCLAIMER}

    @app.get("/ready", tags=["ops"])
    async def ready():
        """Readiness: database reachable and rules KB loaded."""
        try:
            async with maker()() as db:
                await db.execute(text("SELECT 1"))
                claims = (await db.execute(select(func.count()).select_from(Claim))).scalar_one()
        except Exception:  # noqa: BLE001
            return JSONResponse({"status": "unavailable", "database": False}, status_code=503)
        return {"status": "ready", "database": True, "kb_claims": claims, "demo_mode": get_settings().demo_mode,
                "data_region": get_settings().data_region}

    @app.get("/metrics", tags=["ops"], include_in_schema=False)
    async def prometheus(request: Request):
        token = get_settings().metrics_token
        if token and not hmac.compare_digest(request.headers.get("authorization", ""), f"Bearer {token}"):
            return Response(status_code=401)
        return Response(metrics.render(), media_type="text/plain; version=0.0.4")

    return app


app = create_app()
