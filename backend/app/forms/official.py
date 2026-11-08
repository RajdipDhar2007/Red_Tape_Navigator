"""Official form sources: fetch the current PDF from the issuing authority, check it fits our field map, and let a
human approve it. Nothing a citizen sees ever comes from an unapproved download.

Lifecycle of a FormSource:  candidate --(admin activates, only if compatible)--> active --(newer one activated)--> superseded
                            candidate --(admin rejects)--> rejected
A fetch that returns the same bytes as the newest known copy is a no-op; different bytes become a new candidate and
an officer review item ("official form changed") while the previously approved copy keeps serving citizens.
"""
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

import pymupdf
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import audit
from app.db.models import FormSource, ReviewItem
from app.forms.registry import FormTemplate, get_template, load_templates
from app.scraping.fetcher import BinaryFile, fetch_pdf

PdfFetcher = Callable[..., Awaitable[BinaryFile]]


class FormSourceError(ValueError):
    pass


def compat_report(t: FormTemplate, pdf: bytes) -> dict:
    """Does this PDF fit the template's field map? Only AcroForm templates can be verified automatically."""
    try:
        doc = pymupdf.open(stream=pdf, filetype="pdf")
    except Exception as exc:  # noqa: BLE001 - corrupt/encrypted file
        return {"compatible": False, "reason": f"unreadable PDF ({type(exc).__name__})", "pages": 0}
    try:
        pages = doc.page_count
        if doc.needs_pass or doc.is_encrypted:
            return {"compatible": False, "reason": "PDF is password-protected", "pages": pages}
        names = {w.field_name for page in doc for w in (page.widgets() or [])}  # type: ignore[attr-defined]
    finally:
        doc.close()
    mapped = {f.pdf_field for f in t.fields}
    required = {f.pdf_field for f in t.fields if f.required}
    missing_required = sorted(required - names)
    report = {
        "pages": pages, "pdf_fields": len(names), "matched": len(mapped & names),
        "missing_required": missing_required, "missing_optional": sorted((mapped - required) - names),
        "unmapped_in_pdf": sorted(names - mapped),
    }
    if t.kind != "acroform":
        report |= {"compatible": False, "reason": "flat template: overlay coordinates depend on the exact page layout and must be re-mapped by hand"}
    elif not names:
        report |= {"compatible": False, "reason": "PDF has no fillable fields (scanned or flat); re-map the template as an overlay"}
    elif missing_required:
        report |= {"compatible": False, "reason": f"{len(missing_required)} required field(s) of our map are missing from this PDF; update the template field map"}
    else:
        report |= {"compatible": True, "reason": "all required fields of the template map exist in this PDF"}
    return report


async def latest_source(db: AsyncSession, form_id: str) -> FormSource | None:
    return (await db.execute(
        select(FormSource).where(FormSource.form_id == form_id).order_by(FormSource.fetched_at.desc()).limit(1)
    )).scalar_one_or_none()


async def active_source(db: AsyncSession, form_id: str) -> FormSource | None:
    return (await db.execute(
        select(FormSource).where(FormSource.form_id == form_id, FormSource.status == "active")
    )).scalar_one_or_none()


async def fetch_candidate(
    db: AsyncSession, form_id: str, url: str | None = None, *, actor: str = "agent", fetcher: PdfFetcher | None = None
) -> tuple[FormSource, bool]:
    """Fetch the official PDF. Returns (source, is_new). An unchanged file returns the existing row."""
    t = get_template(form_id)
    url = url or t.official_url
    if not url:
        raise FormSourceError("no official URL known for this form; pass one (it must be on the official allowlist)")
    file = await (fetcher or fetch_pdf)(url)
    prev = await latest_source(db, form_id)
    same = (await db.execute(select(FormSource).where(FormSource.form_id == form_id, FormSource.sha256 == file.sha256))).scalars().first()
    if same is not None and same.status != "rejected":
        return same, False
    report = compat_report(t, file.content)
    src = FormSource(form_id=form_id, url=file.url, sha256=file.sha256, size=len(file.content), fetched_at=file.fetched_at,
                     compatible=bool(report["compatible"]), compat=report, pdf=file.content)
    db.add(src)
    if await active_source(db, form_id) is not None or prev is not None:
        db.add(ReviewItem(reason=f"Official form changed or new copy fetched: {form_id} ({file.sha256[:12]}); review and activate"))
    await db.commit()
    await audit.record(db, actor, "form.fetched", {"form": form_id, "sha256": file.sha256, "compatible": src.compatible})
    return src, True


async def decide(db: AsyncSession, source_id: str, *, activate: bool, actor: str) -> FormSource:
    src = await db.get(FormSource, source_id)
    if src is None:
        raise FormSourceError("unknown form source")
    if activate:
        if not src.compatible:
            raise FormSourceError("this PDF does not fit the template's field map; fix the map first. " + str(src.compat.get("reason", "")))
        old = await active_source(db, src.form_id)
        if old is not None and old.id != src.id:
            old.status = "superseded"
        src.status = "active"
    else:
        if src.status == "active":
            raise FormSourceError("cannot reject the active copy; activate another one instead")
        src.status = "rejected"
    src.decided_by, src.decided_at = actor, datetime.now(UTC)
    await db.commit()
    await audit.record(db, actor, "form.activated" if activate else "form.rejected", {"form": src.form_id, "sha256": src.sha256})
    return src


async def check_for_changes(db: AsyncSession, *, fetcher: PdfFetcher | None = None) -> dict:
    """Scheduled: re-fetch every form that has an official URL. Changed files become candidates for human review."""
    out: dict = {"checked": 0, "unchanged": 0, "changed": [], "errors": []}
    for fid, t in load_templates().items():
        active = await active_source(db, fid)
        url = (active.url if active else None) or t.official_url
        if not url:
            continue
        out["checked"] += 1
        try:
            _, new = await fetch_candidate(db, fid, url, actor="agent", fetcher=fetcher)
        except Exception as exc:  # noqa: BLE001 - report each failure, keep going
            out["errors"].append({"form": fid, "error": type(exc).__name__})
            continue
        if new:
            out["changed"].append(fid)
        else:
            out["unchanged"] += 1
    return out


def describe(src: FormSource) -> dict:
    return {"id": src.id, "form_id": src.form_id, "url": src.url, "sha256": src.sha256, "size": src.size, "status": src.status,
            "fetched_at": src.fetched_at.isoformat(), "compatible": src.compatible, "compat": src.compat,
            "decided_by": src.decided_by, "decided_at": src.decided_at.isoformat() if src.decided_at else None}
