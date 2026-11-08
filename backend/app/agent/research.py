"""B. Research agent: KB lookup, optional live verification with grounded extraction, change detection.

Rules:
- Only allowlisted official domains are fetched (enforced in app.scraping.allowlist).
- Scraped text is sanitised and delimited; the LLM may only extract claims whose `quote` appears verbatim in the page.
- Every stored claim has source_url, fetched_at, content_hash. Low confidence => `needs_verification` + review queue.
"""
import asyncio
import re
from collections.abc import Awaitable, Callable

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.llm import LLM, SYSTEM_GUARD
from app.agent.planner import build_plan, licences_for, scope_for
from app.core import audit
from app.core.metrics import LOW_CONFIDENCE
from app.core.tracing import span
from app.db.models import Claim, ReviewItem, SourceSnapshot
from app.kb import confidence as conf
from app.kb.catalog import ACTIVITIES
from app.kb.seed_loader import seed_all
from app.kb.store import ClaimDraft, claims_for_prefixes, upsert_claim
from app.scraping.fetcher import HumanHandoffRequired, Page, fetch_page
from app.scraping.sanitizer import content_hash, wrap_untrusted

Fetcher = Callable[[str], Awaitable[Page]]
_seed_lock = asyncio.Lock()
DISCLAIMER = "AI-assisted guidance, not legal advice. Verify with the issuing authority."


class ExtractedClaim(BaseModel):
    category: str  # requirement | authority | fee | timeline | documents | form_link
    text: str
    quote: str  # verbatim excerpt from the source supporting `text`


class ExtractedClaims(BaseModel):
    claims: list[ExtractedClaim]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def quote_is_grounded(quote: str, page_text: str) -> bool:
    q = _norm(quote)
    return len(q) >= 12 and q in _norm(page_text)


def claim_dict(c: Claim) -> dict:
    return {
        "id": c.id, "key": c.key, "category": c.category, "text": c.text, "data": c.data,
        "source_url": c.source_url, "fetched_at": c.fetched_at.isoformat(), "content_hash": c.content_hash,
        "confidence": c.confidence, "needs_verification": c.needs_verification, "seed": c.seed, "version": c.version,
        "verify_note": "Verify with the authority" if c.needs_verification else None,
    }


async def extract_from_page(llm: LLM, page: Page, licence: str, scope: str) -> list[ClaimDraft]:
    """LLM extraction with verbatim-quote grounding. Ungrounded claims are dropped."""
    out = await llm.structured(
        SYSTEM_GUARD,
        f"Extract fee, timeline, documents, authority, requirement facts for the licence '{licence}'.\n"
        + wrap_untrusted(page.text[:20000], page.url),
        ExtractedClaims,
    )
    drafts = []
    for ec in out.claims:
        if ec.category not in ("requirement", "authority", "fee", "timeline", "documents", "form_link"):
            continue
        if not quote_is_grounded(ec.quote, page.text):
            continue
        drafts.append(ClaimDraft(
            key=f"{licence}:{scope}:{ec.category}", category=ec.category, text=ec.text[:1000],
            data={"licence": licence, "quote": ec.quote[:500], "value": ec.text[:500]}, source_url=page.url,
            fetched_at=page.fetched_at, content_hash=content_hash(ec.text + page.content_hash),
            confidence=conf.score(base=0.8, official_domain=True, verified_live=True, quote_grounded=True),
        ))
    return drafts


async def verify_live(
    db: AsyncSession, claims: list[Claim], *, llm: LLM | None, fetcher: Fetcher = fetch_page, session_id: str | None = None
) -> dict:
    """Fetch each distinct source once; detect changes; optionally upgrade claims through grounded extraction."""
    report: dict = {"fetched": 0, "changed_sources": [], "handoff": [], "errors": []}
    by_url: dict[str, list[Claim]] = {}
    for c in claims:
        by_url.setdefault(c.source_url, []).append(c)
    for url, group in by_url.items():
        try:
            page = await fetcher(url)
        except HumanHandoffRequired as exc:
            report["handoff"].append({"url": url, "message": str(exc)})
            continue
        except Exception as exc:  # noqa: BLE001 - graceful degradation
            report["errors"].append({"url": url, "error": type(exc).__name__})
            continue
        report["fetched"] += 1
        await audit.record(db, "agent", "source.fetched", {"url": url, "hash": page.content_hash, "injection_suspected": page.injection_suspected}, session_id)
        snap = await db.get(SourceSnapshot, url)
        if snap and snap.content_hash != page.content_hash:
            report["changed_sources"].append(url)
            for c in group:
                c.needs_verification = True
                db.add(ReviewItem(session_id=session_id, claim_id=c.id, reason="source page changed since last fetch"))
            await audit.record(db, "agent", "source.changed", {"url": url}, session_id)
        if snap:
            snap.content_hash, snap.fetched_at, snap.excerpt = page.content_hash, page.fetched_at, page.text[:500]
        else:
            db.add(SourceSnapshot(url=url, content_hash=page.content_hash, fetched_at=page.fetched_at, excerpt=page.text[:500]))
        await db.commit()
        if llm and llm.available and not page.injection_suspected:
            seen = set()
            for c in group:
                lic, scope = c.key.split(":")[0], c.key.split(":")[1]
                if (lic, scope) in seen:
                    continue
                seen.add((lic, scope))
                try:
                    for d in await extract_from_page(llm, page, lic, scope):
                        await upsert_claim(db, d)
                except Exception as exc:  # noqa: BLE001
                    report["errors"].append({"url": url, "error": f"extract:{type(exc).__name__}"})
    return report


async def research(
    db: AsyncSession, parsed: dict, *, session_id: str | None = None, llm: LLM | None = None,
    live: bool = False, fetcher: Fetcher = fetch_page,
) -> dict:
    """Return the plan with cited claims. Degrades to the seed KB when live research is off or fails."""
    activity = parsed.get("activity")
    if activity not in ACTIVITIES:
        return {"plan": build_plan(parsed, {}), "claims": [], "low_confidence": [], "mode": "none", "disclaimer": DISCLAIMER}
    needed = licences_for(activity)
    prefixes = [f"{lid}:{scope_for(lid, parsed.get('city'))}:" for lid in needed if scope_for(lid, parsed.get("city"))]
    claims = await claims_for_prefixes(db, prefixes)
    if len(claims) < len(prefixes):  # KB cold start: load the curated seed pack (once, even under concurrency)
        async with _seed_lock:
            claims = await claims_for_prefixes(db, prefixes)
            if len(claims) < len(prefixes):
                await seed_all(db)
                claims = await claims_for_prefixes(db, prefixes)
    live_report = None
    mode = "knowledge_base"
    if live:
        with span("research.live", sources=len({c.source_url for c in claims})):
            live_report = await verify_live(db, claims, llm=llm, fetcher=fetcher, session_id=session_id)
        claims = await claims_for_prefixes(db, prefixes)
        mode = "live_verified" if live_report["fetched"] else "knowledge_base_degraded"
    by_key = {c.key: claim_dict(c) for c in claims}
    plan = build_plan(parsed, by_key)
    if ACTIVITIES[activity].get("general"):
        label = parsed.get("activity_label") or "unspecified"
        plan["note"] = (
            f"Your business type (\"{label}\") is not in our rules pack, so this is the baseline checklist most shops need. "
            "Activity-specific licences may also apply; an officer will confirm which."
        )
        already = (await db.execute(select(ReviewItem).where(ReviewItem.session_id == session_id, ReviewItem.claim_id.is_(None)))).first()
        if session_id and not already:
            db.add(ReviewItem(session_id=session_id, claim_id=None, reason=f"Activity outside rules pack: '{label}' - confirm activity-specific licences"))
    low = [claim_dict(c) for c in claims if c.needs_verification]
    LOW_CONFIDENCE.inc(len(low))
    for c in claims:
        if c.needs_verification:
            existing = (await db.execute(select(ReviewItem).where(ReviewItem.claim_id == c.id, ReviewItem.session_id == session_id))).first()
            if not existing:
                db.add(ReviewItem(session_id=session_id, claim_id=c.id, reason=f"low confidence ({c.confidence})"))
    await db.commit()
    await audit.record(db, "agent", "research.completed", {"claims": len(claims), "low_confidence": len(low), "mode": mode}, session_id)
    return {
        "plan": plan, "claims": list(by_key.values()), "low_confidence": low, "mode": mode,
        "live_report": live_report, "disclaimer": DISCLAIMER,
        "escalation": {"available": True, "message": "Low-confidence items are queued for a CSC operator / officer to verify."} if low else None,
    }


async def refresh_all(db: AsyncSession, *, llm: LLM | None = None, fetcher: Fetcher = fetch_page) -> dict:
    """Scheduled job: re-fetch every source URL in the KB and flag changes."""
    claims = (await db.execute(select(Claim).where(Claim.current.is_(True)))).scalars().all()
    return await verify_live(db, list(claims), llm=llm, fetcher=fetcher)
