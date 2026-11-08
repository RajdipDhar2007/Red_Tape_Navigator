"""Inbound provider webhooks. Digio signs the raw body with HMAC-SHA256 (hex) using the account's webhook secret and
sends it in ``X-Digio-Checksum``; sandbox/production source IPs are published by Digio (docs.digio.in FAQ).

Digio's guidance (and its retry/disable behaviour) is to never fail an authentic delivery: unknown entities and
irrelevant events are logged and answered with 200. Only an invalid checksum / disallowed source is refused.
"""
import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import audit
from app.core.config import get_settings
from app.core.middleware import _client_ip
from app.db.models import ExternalRequest, WebhookEvent
from app.db.session import get_db
from app.integrations.interfaces import (
    STATUS_COMPLETED,
    STATUS_EXPIRED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_REJECTED,
    TERMINAL_STATUSES,
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
log = logging.getLogger(__name__)
MAX_BODY = 1_000_000

_SIGN_EVENTS = {"doc.signed": STATUS_COMPLETED, "doc.sign.failed": STATUS_FAILED, "doc.sign.rejected": STATUS_REJECTED}
_KYC_EVENTS = {
    "documents_pulled_successfully": STATUS_COMPLETED,
    "documents_pulled_partially": STATUS_PENDING,
    "kyc_request_approved": STATUS_COMPLETED,
    "kyc_request_rejected": STATUS_REJECTED,
    "kyc_request_terminated": STATUS_FAILED,
    "kyc_request_expired": STATUS_EXPIRED,
}


def checksum_ok(secret: str, body: bytes, header: str) -> bool:
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, (header or "").strip().lower())


def _targets(event: str, payload: dict) -> tuple[list[str], str | None, dict]:
    """(external ids / our reference ids to look up, new status or None, safe metadata)."""
    if event in _SIGN_EVENTS:
        doc = payload.get("document") or {}
        meta = {k: doc[k] for k in ("error_code",) if doc.get(k)}
        return [str(doc.get("id", ""))], _SIGN_EVENTS[event], meta
    if event in _KYC_EVENTS:
        dl = payload.get("DIGILOCKER_REQUEST") or {}
        kyc = payload.get("KYC_REQUEST") or {}
        ids = [str(x) for x in (dl.get("kyc_request_id"), kyc.get("id"), dl.get("id"), dl.get("reference_id"), kyc.get("reference_id")) if x]
        return ids, _KYC_EVENTS[event], {}
    return [], None, {}


@router.post("/digio")
async def digio(request: Request, db: AsyncSession = Depends(get_db)):
    s = get_settings()
    if not s.digio_webhook_secret:
        raise HTTPException(503, "Webhook not configured")
    if s.digio_ip_list and s.trust_proxy and _client_ip(request) not in s.digio_ip_list:
        raise HTTPException(403, "Source not allowed")
    body = await request.body()
    if len(body) > MAX_BODY:
        raise HTTPException(413, "Payload too large")
    if not checksum_ok(s.digio_webhook_secret, body, request.headers.get("x-digio-checksum", "")):
        raise HTTPException(401, "Invalid checksum")
    try:
        msg = json.loads(body)
        event = str(msg["event"]).lower()
        wid = str(msg["id"])
    except (ValueError, KeyError, TypeError):
        log.warning("digio webhook: authentic but unparseable payload")
        return {"ok": True}

    db.add(WebhookEvent(id=wid))
    try:
        await db.flush()
    except IntegrityError:  # at-least-once delivery: already processed
        await db.rollback()
        return {"ok": True, "duplicate": True}

    ids, status, meta = _targets(event, msg.get("payload") if isinstance(msg.get("payload"), dict) else {})
    ids = [i for i in ids if i]
    row = None
    if ids and status:
        row = (await db.execute(select(ExternalRequest).where(or_(ExternalRequest.external_id.in_(ids), ExternalRequest.id.in_(ids))))).scalars().first()
    if row is None:
        log.info("digio webhook: event=%s matched no request", event)  # not an error: could be another product or archived data
    elif not (status == STATUS_PENDING and row.status in TERMINAL_STATUSES):  # a late "partial" never undoes a finished request
        row.status = status or row.status
        row.meta = {**(row.meta or {}), **meta}
        await audit.record(db, row.user_id, f"integration.{row.kind}.webhook", {"status": row.status}, row.session_id)
    await db.commit()
    return {"ok": True}
