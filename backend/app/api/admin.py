"""Human escalation (review queue for CSC operators / officers) and admin operations."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.llm import LLM
from app.agent.research import refresh_all
from app.api.deps import require_roles
from app.core import audit
from app.core.config import get_settings
from app.db.models import Claim, Consent, FormSource, NavSession, ReviewItem, User
from app.db.session import get_db
from app.forms import official
from app.forms.registry import load_templates
from app.scraping.allowlist import DomainNotAllowed
from app.scraping.fetcher import HumanHandoffRequired, NotAPdf, RobotsDisallowed
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


@router.get("/stats")
async def stats(user: User = Depends(require_roles(*STAFF)), db: AsyncSession = Depends(get_db)):
    """Aggregate, non-personal programme metrics for officers and oversight bodies."""

    async def count(stmt):
        return (await db.execute(stmt)).scalar_one()

    async def grouped(col, *where):
        rows = (await db.execute(select(col, func.count()).where(*where).group_by(col))).all()
        return {str(k or "unknown"): n for k, n in rows}

    sessions_total = await count(select(func.count()).select_from(NavSession))
    reviewed = await count(select(func.count()).select_from(NavSession).where(NavSession.reviewed_at.is_not(None)))
    by_activity: dict[str, int] = {}
    by_state: dict[str, int] = {}
    for (parsed,) in (await db.execute(select(NavSession.parsed))).all():
        p = parsed or {}
        by_activity[str(p.get("activity") or "unknown")] = by_activity.get(str(p.get("activity") or "unknown"), 0) + 1
        by_state[str(p.get("state") or "unknown")] = by_state.get(str(p.get("state") or "unknown"), 0) + 1
    return {
        "users": {"total": await count(select(func.count()).select_from(User).where(User.deleted_at.is_(None))),
                  "by_role": await grouped(User.role, User.deleted_at.is_(None))},
        "sessions": {"total": sessions_total, "reviewed": reviewed,
                     "completion_rate": round(reviewed / sessions_total, 3) if sessions_total else 0.0,
                     "by_stage": await grouped(NavSession.stage), "by_activity": by_activity, "by_state": by_state},
        "knowledge_base": {
            "claims": await count(select(func.count()).select_from(Claim).where(Claim.current.is_(True))),
            "needs_verification": await count(select(func.count()).select_from(Claim).where(Claim.current.is_(True), Claim.needs_verification.is_(True))),
            "seed_only": await count(select(func.count()).select_from(Claim).where(Claim.current.is_(True), Claim.seed.is_(True))),
        },
        "review_queue": await grouped(ReviewItem.status),
        "consents": {"granted": await count(select(func.count()).select_from(Consent).where(Consent.granted.is_(True))),
                     "withdrawn": await count(select(func.count()).select_from(Consent).where(Consent.granted.is_(False)))},
    }


@router.get("/users")
async def list_users(user: User = Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(User).where(User.deleted_at.is_(None)).order_by(User.created_at))).scalars().all()
    return [{"id": u.id, "email": u.email, "role": u.role, "created_at": u.created_at.isoformat()} for u in rows]


class FetchFormIn(BaseModel):
    url: str | None = Field(default=None, max_length=1024)


@router.get("/forms")
async def list_forms(user: User = Depends(require_roles(*STAFF)), db: AsyncSession = Depends(get_db)):
    """Every form template, whether citizens currently get an approved official copy, and fetched candidates."""
    out = []
    for fid, t in load_templates().items():
        rows = (await db.execute(select(FormSource).where(FormSource.form_id == fid).order_by(FormSource.fetched_at.desc()))).scalars().all()
        active = next((r for r in rows if r.status == "active"), None)
        out.append({
            "form_id": fid, "title": t.title, "authority": t.authority, "official_url": t.official_url,
            "serving": "official" if active else "placeholder", "active": official.describe(active) if active else None,
            "candidates": [official.describe(r) for r in rows if r.status == "candidate"],
        })
    return out


@router.post("/forms/{form_id}/fetch")
async def fetch_form(form_id: str, body: FetchFormIn, user: User = Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    if form_id not in load_templates():
        raise HTTPException(404, "Unknown form")
    try:
        src, is_new = await official.fetch_candidate(db, form_id, body.url, actor=user.id)
    except official.FormSourceError as exc:
        raise HTTPException(422, str(exc)) from exc
    except DomainNotAllowed as exc:
        raise HTTPException(422, f"URL is not on the official allowlist: {exc}") from exc
    except (HumanHandoffRequired, RobotsDisallowed, NotAPdf) as exc:
        raise HTTPException(422, f"Could not fetch a PDF: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 - network failures
        raise HTTPException(502, f"Could not reach the official site ({type(exc).__name__})") from exc
    return {"new": is_new, **official.describe(src)}


@router.get("/forms/sources/{source_id}/pdf")
async def download_source(source_id: str, user: User = Depends(require_roles(*STAFF)), db: AsyncSession = Depends(get_db)):
    from fastapi.responses import Response

    src = await db.get(FormSource, source_id)
    if src is None:
        raise HTTPException(404, "Not found")
    return Response(src.pdf, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{src.form_id}-{src.sha256[:8]}.pdf"'})


@router.post("/forms/sources/{source_id}/{decision}")
async def decide_source(source_id: str, decision: str, user: User = Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    if decision not in ("activate", "reject"):
        raise HTTPException(404, "Not found")
    try:
        src = await official.decide(db, source_id, activate=decision == "activate", actor=user.id)
    except official.FormSourceError as exc:
        raise HTTPException(409, str(exc)) from exc
    return official.describe(src)


@router.post("/forms/refresh")
async def refresh_forms(user: User = Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    return await official.check_for_changes(db)


@router.get("/readiness")
async def operational_readiness(user: User = Depends(require_roles(*STAFF)), db: AsyncSession = Depends(get_db)):
    """Restricted operational readiness check for staff/admins. Never exposes secrets or calls external third-party APIs."""
    s = get_settings()
    db_reachable = False
    try:
        await db.execute(text("SELECT 1"))
        db_reachable = True
    except Exception:  # noqa: BLE001
        db_reachable = False

    redis_configured = bool(s.redis_url.strip())
    redis_reachable: bool | None = None
    if redis_configured:
        try:
            import redis.asyncio as redis_async

            r = redis_async.from_url(s.redis_url, socket_connect_timeout=1.0, socket_timeout=1.0)
            try:
                redis_reachable = bool(await r.ping())
            finally:
                await r.aclose()
        except Exception:  # noqa: BLE001
            redis_reachable = False

    storage_configured = (
        bool(s.storage_local_dir.strip())
        if s.storage_backend == "local"
        else bool(s.storage_bucket and s.storage_region and s.storage_access_key_id and s.storage_secret_access_key)
    )
    scanner_configured = bool(s.document_scan_url.startswith(("https://", "http://"))) if s.document_scan_mode == "external" else False

    return {
        "application": {
            "running": True,
            "env": s.app_env,
            "demo_mode": s.demo_mode,
            "integrations_mode": s.integrations_mode,
        },
        "database": {
            "reachable": db_reachable,
            "engine": "sqlite" if s.database_url.startswith("sqlite") else "postgresql",
        },
        "redis": {
            "configured": redis_configured,
            "reachable": redis_reachable,
        },
        "storage": {
            "backend": s.storage_backend,
            "configured": storage_configured,
            "durable": s.storage_backend == "s3",
            "production_warning": (
                "STORAGE_BACKEND=local in prod relies on local disk; use S3 or a backed-up persistent volume"
                if (s.storage_backend == "local" and s.is_prod)
                else None
            ),
            "scan_mode": s.document_scan_mode,
            "scanner_configured": scanner_configured,
        },
        "providers": {
            "llm": {
                "provider": "anthropic",
                "configured": bool(s.anthropic_api_key.strip() and s.anthropic_model.strip()),
                "model_configured": bool(s.anthropic_model.strip()),
            },
            "smtp": {
                "configured": bool(s.smtp_host.strip() and s.smtp_from.strip()),
                "mode": "live" if (s.smtp_host.strip() and s.smtp_from.strip()) else "mock",
                "tls": "ssl" if s.smtp_port == 465 else ("starttls" if s.smtp_starttls else "plain"),
                "auth_configured": bool(s.smtp_username.strip() and s.smtp_password),
            },
            "msg91": {
                "configured": bool(s.msg91_authkey.strip() and s.msg91_template_id.strip()),
                "mode": "live" if (s.msg91_authkey.strip() and s.msg91_template_id.strip()) else "mock",
            },
            "digio": {
                "configured": s.digio_configured,
                "mode": "live" if s.digio_configured else "mock",
                "env": s.digio_env if s.digio_configured else None,
                "webhook_secret_configured": bool(s.digio_webhook_secret.strip()),
                "webhook_ip_allowlist_configured": bool(s.digio_ip_list),
                "digilocker_field_mapping_ready": False,
            },
            "sentry": {
                "configured": bool(s.sentry_dsn.strip()),
            },
            "otel": {
                "configured": bool(s.otel_exporter_otlp_endpoint.strip()),
            },
            "whatsapp": {
                "configured": False,
                "mode": "stub" if s.integrations_mode == "real" else "mock",
            },
            "umang": {
                "configured": False,
                "mode": "stub" if s.integrations_mode == "real" else "mock",
            },
        },
    }

