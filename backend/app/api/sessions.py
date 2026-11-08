import re
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.intake import apply_general_fallback, parse_goal
from app.agent.llm import LLM
from app.agent.research import DISCLAIMER, research
from app.api.consent import has_consent
from app.api.deps import current_user
from app.core import audit
from app.core.config import get_settings
from app.db.models import NavSession, User
from app.db.session import get_db
from app.followup.checklist import submission_checklist
from app.followup.reminders import schedule_after_submission
from app.forms import filler
from app.forms.registry import get_template
from app.integrations.factory import get_integrations
from app.interview import engine, memory
from app.interview.fields import FIELDS
from app.services import session_service as svc

router = APIRouter(prefix="/sessions", tags=["sessions"])


class GoalIn(BaseModel):
    goal: str = Field(min_length=5, max_length=1000)
    language: str = Field(default="en", pattern="^(en|bn|hi)$")


class ClarifyIn(BaseModel):
    answer: str = Field(min_length=2, max_length=200)


class ResearchIn(BaseModel):
    live: bool = False


class AnswersIn(BaseModel):
    answers: dict[str, str] = Field(max_length=30)


class SkipIn(BaseModel):
    key: str


class EditIn(BaseModel):
    value: str = Field(max_length=300)


class ReviewIn(BaseModel):
    confirm: bool
    acknowledge_incomplete: bool = False


class SubmittedIn(BaseModel):
    licences: list[str] = Field(max_length=12)
    channel: str = Field(default="email", pattern="^(email|sms|whatsapp)$")


class EsignIn(BaseModel):
    form_id: str


def _view(ns: NavSession) -> dict:
    return {
        "id": ns.id, "goal": ns.goal, "language": ns.language, "parsed": ns.parsed, "plan": ns.plan,
        "skipped": ns.skipped, "reviewed": ns.reviewed_at is not None, "created_at": ns.created_at.isoformat(),
        "disclaimer": DISCLAIMER,
    }


@router.post("", status_code=201)
async def create(body: GoalIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    if not await has_consent(db, user.id, "service"):
        raise HTTPException(403, {"code": "consent_required", "message": "Please accept the data-use notice first."})
    ns = svc.new_session(user, body.goal, body.language)
    db.add(ns)
    await db.commit()
    llm = LLM()
    parsed = await parse_goal(body.goal, body.language, llm)
    ns.parsed = parsed.model_dump()
    await db.commit()
    if not parsed.clarifying_question and parsed.activity:
        await memory.seed_derived(db, ns)
    await audit.record(db, user.id, "session.created", {"activity": parsed.activity, "city": parsed.city, "state": parsed.state}, ns.id)
    out = _view(ns)
    out["tracker"] = await svc.tracker(db, ns)
    out["agent_mode"] = "llm" if llm.available else "rules_fallback"
    return out


@router.post("/{sid}/clarify")
async def clarify(sid: str, body: ClarifyIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    ns = await svc.get_owned(db, user, sid)
    parsed = await parse_goal(f"{ns.goal}. {body.answer}", ns.language, LLM())
    parsed = apply_general_fallback(parsed, body.answer)
    ns.parsed = parsed.model_dump()
    await db.commit()
    if not parsed.clarifying_question and parsed.activity:
        await memory.seed_derived(db, ns)
    await audit.record(db, user.id, "session.clarified", {"city": parsed.city, "state": parsed.state}, ns.id)
    return {**_view(ns), "tracker": await svc.tracker(db, ns)}


@router.get("/{sid}")
async def get(sid: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    ns = await svc.get_owned(db, user, sid)
    return {**_view(ns), "tracker": await svc.tracker(db, ns)}


@router.post("/{sid}/research")
async def run_research(sid: str, body: ResearchIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    ns = await svc.get_owned(db, user, sid)
    p = ns.parsed or {}
    if p.get("clarifying_question") or not p.get("activity"):
        raise HTTPException(409, {"code": "goal_incomplete", "message": p.get("clarifying_question") or "Tell us what kind of business this is."})
    live = body.live and not get_settings().demo_mode
    res = await research(db, p, session_id=ns.id, llm=LLM(), live=live)
    ns.plan = res["plan"]
    await db.commit()
    return {**res, "tracker": await svc.tracker(db, ns), "live_requested_but_disabled": body.live and not live}


@router.get("/{sid}/checklist")
async def checklist(sid: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    ns = await svc.get_owned(db, user, sid)
    return {"plan": ns.plan, "required_fields": sorted(svc.required_keys(ns)), "disclaimer": DISCLAIMER}


@router.get("/{sid}/interview")
async def interview(sid: str, include_skipped: bool = False, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    ns = await svc.get_owned(db, user, sid)
    st = await engine.state(db, ns, svc.required_keys(ns), include_skipped=include_skipped)
    return {**st, "tracker": await svc.tracker(db, ns)}


@router.post("/{sid}/interview")
async def answer(sid: str, body: AnswersIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    ns = await svc.get_owned(db, user, sid)
    res = await engine.submit(db, ns, body.answers)
    # audit keys only, never values
    await audit.record(db, user.id, "interview.answered", {"keys": sorted(res["saved"]), "rejected": sorted(res["errors"])}, ns.id)
    st = await engine.state(db, ns, svc.required_keys(ns))
    return {**res, "next": st, "tracker": await svc.tracker(db, ns)}


@router.post("/{sid}/interview/skip")
async def skip(sid: str, body: SkipIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    ns = await svc.get_owned(db, user, sid)
    try:
        await memory.skip(db, ns, body.key)
    except memory.AnswerError as exc:
        raise HTTPException(422, "Unknown field") from exc
    return await engine.state(db, ns, svc.required_keys(ns))


@router.get("/{sid}/answers")
async def answers(sid: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    ns = await svc.get_owned(db, user, sid)
    data = await memory.get_answers(db, ns.id)
    lang = ns.language if ns.language in ("en", "bn", "hi") else "en"
    return {k: {**v, "label": FIELDS[k].label[lang] if k in FIELDS else k} for k, v in data.items()}


@router.put("/{sid}/answers/{key}")
async def edit_answer(sid: str, key: str, body: EditIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    ns = await svc.get_owned(db, user, sid)
    try:
        val = await memory.set_answer(db, ns.id, key, body.value)
    except memory.AnswerError as exc:
        raise HTTPException(422, {"code": exc.code, "message": engine.error_message(exc.code, ns.language)}) from exc
    await audit.record(db, user.id, "answer.edited", {"key": key}, ns.id)
    return {"key": key, "value": "***" if key in FIELDS and FIELDS[key].sensitive else val}


@router.delete("/{sid}/answers/{key}", status_code=204)
async def delete_answer(sid: str, key: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    ns = await svc.get_owned(db, user, sid)
    await memory.delete_answer(db, ns.id, key)
    ns.reviewed_at = None
    await db.commit()
    await audit.record(db, user.id, "answer.deleted", {"key": key}, ns.id)
    return Response(status_code=204)


@router.post("/{sid}/documents/digilocker")
async def digilocker_import(sid: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    ns = await svc.get_owned(db, user, sid)
    integ = get_integrations()
    if integ.mode == "mock" and not get_settings().demo_mode:
        raise HTTPException(503, "DigiLocker is not connected")
    res = await integ.digilocker.fetch_document(user.id, "demo-aadhaar")
    existing = await memory.get_answers(db, ns.id)
    saved = []
    for k, v in res.data["fields"].items():
        if k not in existing:  # never overwrite what the user already told us
            await memory.set_answer(db, ns.id, k, v, source="document")
            saved.append(k)
    await audit.record(db, user.id, "integration.digilocker", {"mock": res.mock, "keys": saved}, ns.id)
    return {"imported": saved, "mock": res.mock, "label": res.label}


# ---------- F. Review checkpoint ----------


def plain_summary(ns: NavSession) -> dict:
    lang = ns.language if ns.language in ("en", "bn", "hi") else "en"
    heads = {
        "en": ("Authority", "Fee", "Timeline", "Documents"),
        "bn": ("কর্তৃপক্ষ", "ফি", "সময়", "কাগজপত্র"),
        "hi": ("प्राधिकरण", "शुल्क", "समय", "दस्तावेज़"),
    }[lang]
    steps = []
    for s in (ns.plan or {}).get("steps", []):
        c = s.get("claims", {})
        lines = []
        for lab, key in zip(heads, ("authority", "fee", "timeline", "documents"), strict=True):
            cl = c.get(key)
            lines.append({
                "label": lab,
                "text": cl["text"] if cl else None,
                "citation": {
                    "source_url": cl["source_url"], "fetched_at": cl["fetched_at"], "content_hash": cl["content_hash"],
                    "confidence": cl["confidence"], "verify_with_authority": cl["needs_verification"],
                } if cl else None,
            })
        steps.append({"order": s["order"], "name": s["name"], "conditional": s["conditional"],
                      "municipal_data_missing": s.get("municipal_data_missing", False), "lines": lines})
    return {"steps": steps, "disclaimer": DISCLAIMER, "note": "Regulatory text is shown in English as published by the authority."}


@router.get("/{sid}/review")
async def review(sid: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    ns = await svc.get_owned(db, user, sid)
    fills = await svc.fill_all(db, ns)
    ans = await memory.get_answers(db, ns.id)
    forms = []
    for fid, r in fills.items():
        rows = r.report_dicts()
        tpl_fields = {f.pdf_field: f for f in get_template(fid).fields}
        for row in rows:
            f = tpl_fields.get(row["pdf_field"])
            keys = f.keys if f else []
            key = keys[0] if len(keys) == 1 and keys[0] in FIELDS else None
            row["answer_key"] = key
            row["editable"] = key is not None
            row["answer_value"] = ans.get(key, {}).get("value") if key else None
        forms.append({
            "form_id": fid, "title": r.title, "placeholder": r.placeholder, "summary": r.summary(),
            "warnings": r.warnings, "fields": rows, "preview_url": f"/sessions/{sid}/forms/{fid}/preview.png",
        })
    return {
        "forms": forms, "summary": plain_summary(ns), "reviewed": ns.reviewed_at is not None, "disclaimer": DISCLAIMER,
        "consent_statement": "I have reviewed these forms and the information in them is correct. I understand I must sign and submit them myself.",
    }


@router.get("/{sid}/forms/{fid}/preview.png")
async def preview(sid: str, fid: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    ns = await svc.get_owned(db, user, sid)
    fills = await svc.fill_all(db, ns)
    if fid not in fills:
        raise HTTPException(404, "Unknown form")
    return Response(filler.render_preview_png(fills[fid].pdf), media_type="image/png", headers={"Cache-Control": "no-store"})


@router.post("/{sid}/review")
async def confirm_review(sid: str, body: ReviewIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    """The explicit human consent step. Nothing downloadable or signable exists before this."""
    ns = await svc.get_owned(db, user, sid)
    if not body.confirm:
        raise HTTPException(422, "Explicit confirmation required")
    fills = await svc.fill_all(db, ns)
    if not fills:
        raise HTTPException(409, "Nothing to review: run research first")
    missing = {fid: [r.label for r in f.report if r.status == "missing"] for fid, f in fills.items()}
    missing = {k: v for k, v in missing.items() if v}
    if missing and not body.acknowledge_incomplete:
        raise HTTPException(409, {"code": "incomplete", "message": "Some required fields are missing. Complete them or acknowledge they will be filled by hand.", "missing": missing})
    ns.reviewed_at = datetime.now(UTC)
    ns.stage = "submit"
    ns.plan = {**ns.plan, "_review": {"incomplete_acknowledged": bool(missing), "form_hashes": {fid: svc.sha256(f.pdf) for fid, f in fills.items()}}}
    await db.commit()
    await audit.record(db, user.id, "review.confirmed", {"forms": list(fills), "incomplete_ack": bool(missing)}, ns.id)
    return {"reviewed": True, "reviewed_at": ns.reviewed_at.isoformat()}


def _require_reviewed(ns: NavSession) -> None:
    if ns.reviewed_at is None:
        raise HTTPException(403, {"code": "review_required", "message": "Review and confirm your forms before downloading or signing."})


@router.get("/{sid}/forms/{fid}/download")
async def download(sid: str, fid: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    ns = await svc.get_owned(db, user, sid)
    _require_reviewed(ns)
    fills = await svc.fill_all(db, ns)
    if fid not in fills:
        raise HTTPException(404, "Unknown form")
    await audit.record(db, user.id, "form.downloaded", {"form": fid}, ns.id)
    name = re.sub(r"[^a-z0-9_]", "", fid)
    return Response(fills[fid].pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{name}.pdf"', "X-Disclaimer": DISCLAIMER})


@router.get("/{sid}/submission-checklist")
async def submission(sid: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    ns = await svc.get_owned(db, user, sid)
    _require_reviewed(ns)
    return {
        "items": submission_checklist(ns.plan, set(svc.form_ids(ns))), "disclaimer": DISCLAIMER,
        "important": "You submit every application yourself on the official portal. This tool never submits anything on your behalf.",
    }


@router.post("/{sid}/esign")
async def esign(sid: str, body: EsignIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    ns = await svc.get_owned(db, user, sid)
    _require_reviewed(ns)
    fills = await svc.fill_all(db, ns)
    if body.form_id not in fills:
        raise HTTPException(404, "Unknown form")
    res = await get_integrations().esign.request_signature(svc.sha256(fills[body.form_id].pdf), user.id)
    await audit.record(db, user.id, "integration.esign", {"form": body.form_id, "mock": res.mock}, ns.id)
    return {"mock": res.mock, "label": res.label, **res.data}


@router.post("/{sid}/submitted")
async def i_submitted(sid: str, body: SubmittedIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    """The CITIZEN tells us they submitted; we only schedule reminders. We never submit anything."""
    ns = await svc.get_owned(db, user, sid)
    _require_reviewed(ns)
    if not await has_consent(db, user.id, "reminders"):
        raise HTTPException(403, {"code": "consent_required", "message": "Reminders need your consent."})
    valid = {s["licence"] for s in ns.plan.get("steps", [])}
    bad = [x for x in body.licences if x not in valid]
    if bad:
        raise HTTPException(422, f"Not in your plan: {bad}")
    ans = await memory.get_answers(db, ns.id, reveal=True)
    dest = user.email if body.channel == "email" else ans.get("mobile", {}).get("value", "")
    if not dest:
        raise HTTPException(422, "No destination for this channel; provide your mobile number first")
    rows = await schedule_after_submission(db, session_id=ns.id, user_id=user.id, licences=body.licences, channel=body.channel, destination=dest)
    await audit.record(db, user.id, "followup.scheduled", {"count": len(rows), "channel": body.channel}, ns.id)
    return {"scheduled": [{"title": r.title, "due_at": r.due_at.isoformat(), "kind": r.kind} for r in rows]}
