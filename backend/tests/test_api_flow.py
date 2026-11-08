"""End-to-end API test of the demo scenario: bakery in Kolkata -> research -> interview -> filled PDFs -> review."""
import json
import pathlib
import re

import pymupdf

from app.core import audit
from app.db.models import Reminder, User
from app.db.session import maker
from app.followup.reminders import dispatch_due
from app.integrations.factory import get_integrations
from app.integrations.mock import MockMessenger
from tests.test_interview import make_valid_aadhaar

ANSWERS = {
    "applicant_name": "Asha Roy", "father_name": "Ravi Roy", "dob": "14/03/1990", "gender": "female",
    "social_category": "general", "aadhaar": make_valid_aadhaar(), "pan": "ABCPE1234F", "mobile": "9876543210",
    "email": "asha@example.com", "residence_address": "12 Park Street, Kolkata", "residence_pincode": "700016",
    "business_name": "Sweet Crumbs Bakery", "organisation_type": "proprietorship", "date_of_commencement": "01/01/2027",
    "food_products": "Bread, cakes, cookies", "num_employees": "3", "annual_turnover": "900000", "investment_amount": "400000",
    "premises_address": "5 College Street, Kolkata", "premises_pincode": "700073", "premises_ownership": "rented",
    "premises_area_sqft": "350", "bank_account_number": "123456789012", "bank_ifsc": "SBIN0001234",
}


async def start(client, auth, goal="I want to open a small bakery in Kolkata", language="en"):
    headers, _ = auth
    await client.post("/consent", json={"purpose": "service", "granted": True}, headers=headers)
    r = await client.post("/sessions", json={"goal": goal, "language": language}, headers=headers)
    assert r.status_code == 201, r.text
    return headers, r.json()


async def test_requires_consent_first(client, auth):
    headers, _ = auth
    r = await client.post("/sessions", json={"goal": "bakery in Kolkata"}, headers=headers)
    assert r.status_code == 403 and r.json()["detail"]["code"] == "consent_required"


async def test_full_demo_flow(client, auth):
    headers, s = await start(client, auth)
    sid = s["id"]
    assert s["parsed"]["city"] == "Kolkata" and s["agent_mode"] == "rules_fallback" and s["disclaimer"]
    assert s["tracker"]["current"] == "research"

    # research -> checklist, every claim cited
    r = (await client.post(f"/sessions/{sid}/research", json={}, headers=headers)).json()
    assert [x["licence"] for x in r["plan"]["steps"]][:4] == ["udyam", "fssai", "trade_licence", "fire_noc"]
    assert all(c["source_url"] and c["content_hash"] and c["fetched_at"] for c in r["claims"])
    assert r["tracker"]["current"] == "checklist" and r["disclaimer"]
    chk = (await client.get(f"/sessions/{sid}/checklist", headers=headers)).json()
    assert "applicant_name" in chk["required_fields"] and "city" not in chk["required_fields"]

    # interview: only missing details, 1-2 at a time, never repeated
    asked = []
    for _ in range(40):
        st = (await client.get(f"/sessions/{sid}/interview", headers=headers)).json()
        if not st["questions"]:
            break
        assert 1 <= len(st["questions"]) <= 2
        keys = [q["key"] for q in st["questions"]]
        assert not set(keys) & set(asked), "asked the same thing twice"
        asked += keys
        res = (await client.post(f"/sessions/{sid}/interview", json={"answers": {k: ANSWERS[k] for k in keys}}, headers=headers)).json()
        assert not res["errors"], res["errors"]
    assert st["complete"] and st["progress"]["percent"] == 100
    assert set(asked) == set(chk["required_fields"])  # asked exactly the union, nothing more

    # review payload: side-by-side data
    rv = (await client.get(f"/sessions/{sid}/review", headers=headers)).json()
    assert {f["form_id"] for f in rv["forms"]} == {"udyam_details", "fssai_form_a", "trade_licence"}
    fssai = next(f for f in rv["forms"] if f["form_id"] == "fssai_form_a")
    assert fssai["summary"].get("missing", 0) == 0 and fssai["placeholder"]
    assert any(f["editable"] and f["answer_key"] == "applicant_name" for f in fssai["fields"])
    assert all(line["citation"] for step in rv["summary"]["steps"] for line in step["lines"] if line["text"])
    assert "AI-assisted guidance" in rv["disclaimer"]
    assert (await client.get(f"/sessions/{sid}/forms/fssai_form_a/preview.png", headers=headers)).content[:4] == b"\x89PNG"

    # NOTHING downloadable/signable before explicit consent
    for method, url, kw in [("get", f"/sessions/{sid}/forms/fssai_form_a/download", {}), ("get", f"/sessions/{sid}/submission-checklist", {}),
                            ("post", f"/sessions/{sid}/esign", {"json": {"form_id": "fssai_form_a"}})]:
        r = await getattr(client, method)(url, headers=headers, **kw)
        assert r.status_code == 403 and r.json()["detail"]["code"] == "review_required"
    assert (await client.post(f"/sessions/{sid}/review", json={"confirm": False}, headers=headers)).status_code == 422

    # edit an answer on the right pane -> preview regenerates; then confirm
    assert (await client.put(f"/sessions/{sid}/answers/applicant_name", json={"value": "Asha Devi Roy"}, headers=headers)).status_code == 200
    assert (await client.put(f"/sessions/{sid}/answers/pan", json={"value": "bad"}, headers=headers)).status_code == 422
    assert (await client.post(f"/sessions/{sid}/review", json={"confirm": True}, headers=headers)).status_code == 200

    pdf = await client.get(f"/sessions/{sid}/forms/fssai_form_a/download", headers=headers)
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
    fields = {w.field_name: w.field_value for p in pymupdf.open(stream=pdf.content, filetype="pdf") for w in p.widgets()}
    assert fields["applicant_name"] == "Asha Devi Roy"

    # editing after review invalidates it
    await client.put(f"/sessions/{sid}/answers/mobile", json={"value": "9123456789"}, headers=headers)
    assert (await client.get(f"/sessions/{sid}/forms/fssai_form_a/download", headers=headers)).status_code == 403
    await client.post(f"/sessions/{sid}/review", json={"confirm": True}, headers=headers)

    cl = (await client.get(f"/sessions/{sid}/submission-checklist", headers=headers)).json()
    assert "never submits" in cl["important"] and cl["items"][0]["licence"] == "udyam"
    assert any("yourself" in a for a in cl["items"][0]["actions"])

    # mock e-sign is labelled and not legally valid
    es = (await client.post(f"/sessions/{sid}/esign", json={"form_id": "udyam_details"}, headers=headers)).json()
    assert es["mock"] and "Demo mode" in es["label"] and es["legally_valid"] is False

    # reminders need consent; created only when the citizen says they submitted
    body = {"licences": ["udyam", "fssai"], "channel": "email"}
    assert (await client.post(f"/sessions/{sid}/submitted", json=body, headers=headers)).status_code == 403
    await client.post("/consent", json={"purpose": "reminders", "granted": True}, headers=headers)
    assert (await client.post(f"/sessions/{sid}/submitted", json={"licences": ["nope"]}, headers=headers)).status_code == 422
    sched = (await client.post(f"/sessions/{sid}/submitted", json=body, headers=headers)).json()["scheduled"]
    assert {x["kind"] for x in sched} == {"status", "renewal"}

    # sensitive data never in audit log; chain intact
    async with maker()() as db:
        assert await audit.verify_chain(db)
        rows = (await db.execute(audit.AuditLog.__table__.select())).all()
        blob = json.dumps([r.detail for r in rows])
        assert ANSWERS["aadhaar"] not in blob and ANSWERS["pan"] not in blob
        assert {"session.created", "review.confirmed", "form.downloaded", "followup.scheduled"} <= {r.action for r in rows}


async def test_ownership_isolation(client, auth):
    headers, s = await start(client, auth)
    r2 = await client.post("/auth/register", json={"email": "other@example.com", "password": "another-long-pass"})
    other = {"Authorization": f"Bearer {r2.json()['access_token']}"}
    assert (await client.get(f"/sessions/{s['id']}", headers=other)).status_code == 404
    assert (await client.get(f"/sessions/{s['id']}/review", headers=other)).status_code == 404


async def test_clarifying_question_flow_and_unknown_city(client, auth):
    headers, s = await start(client, auth, goal="I want to open a bakery")
    assert s["parsed"]["clarifying_question"] and s["tracker"]["current"] == "goal"
    assert (await client.post(f"/sessions/{s['id']}/research", json={}, headers=headers)).status_code == 409
    s2 = (await client.post(f"/sessions/{s['id']}/clarify", json={"answer": "Pune, Maharashtra"}, headers=headers)).json()
    assert s2["parsed"]["city"] == "Pune" and not s2["parsed"]["clarifying_question"]
    assert (await client.post(f"/sessions/{s['id']}/research", json={"live": True}, headers=headers)).json()["live_requested_but_disabled"]


async def test_bengali_flow_and_skip(client, auth):
    headers, s = await start(client, auth, goal="কলকাতায় একটি বেকারি খুলতে চাই", language="bn")
    sid = s["id"]
    assert s["parsed"]["city"] == "Kolkata"
    await client.post(f"/sessions/{sid}/research", json={}, headers=headers)
    st = (await client.get(f"/sessions/{sid}/interview", headers=headers)).json()
    assert re.search(r"[ঀ-৿]", st["questions"][0]["question"])
    key = st["questions"][0]["key"]
    assert (await client.post(f"/sessions/{sid}/interview/skip", json={"key": key}, headers=headers)).status_code == 200
    assert key not in [q["key"] for q in (await client.get(f"/sessions/{sid}/interview", headers=headers)).json()["questions"]]
    assert (await client.post(f"/sessions/{sid}/interview/skip", json={"key": "zzz"}, headers=headers)).status_code == 422
    # incomplete review requires explicit acknowledgement
    r = await client.post(f"/sessions/{sid}/review", json={"confirm": True}, headers=headers)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "incomplete"
    assert (await client.post(f"/sessions/{sid}/review", json={"confirm": True, "acknowledge_incomplete": True}, headers=headers)).status_code == 200
    answers = (await client.get(f"/sessions/{sid}/answers", headers=headers)).json()
    assert "city" in answers
    assert (await client.delete(f"/sessions/{sid}/answers/city", headers=headers)).status_code == 204


async def test_digilocker_mock_labelled_and_no_overwrite(client, auth):
    headers, s = await start(client, auth)
    sid = s["id"]
    await client.post(f"/sessions/{sid}/research", json={}, headers=headers)
    await client.put(f"/sessions/{sid}/answers/applicant_name", json={"value": "Real Person"}, headers=headers)
    r = (await client.post(f"/sessions/{sid}/documents/digilocker", headers=headers)).json()
    assert r["mock"] and "Demo mode" in r["label"] and "applicant_name" not in r["imported"]


async def test_privacy_export_erase_and_purge(client, auth):
    headers, s = await start(client, auth)
    sid = s["id"]
    await client.post(f"/sessions/{sid}/research", json={}, headers=headers)
    await client.post(f"/sessions/{sid}/interview", json={"answers": {"applicant_name": "Asha Roy", "pan": "ABCPE1234F"}}, headers=headers)
    exp = await client.get("/privacy/export", headers=headers)
    data = exp.json()
    assert data["sessions"][0]["answers"]["pan"]["value"] == "ABCPE1234F" and data["consents"]
    assert (await client.get("/privacy/policy")).json()["retention_days"] == 90

    # retention purge removes expired sessions
    from datetime import UTC, datetime, timedelta

    from app.db.models import NavSession
    from app.services.privacy import purge_expired

    async with maker()() as db:
        ns = await db.get(NavSession, sid)
        ns.expires_at = datetime.now(UTC) - timedelta(days=1)
        await db.commit()
        assert await purge_expired(db) == 1
    assert (await client.get(f"/sessions/{sid}", headers=headers)).status_code == 404

    headers2, s2 = await start(client, auth)
    assert (await client.delete(f"/privacy/sessions/{s2['id']}", headers=headers)).status_code == 204
    assert (await client.delete("/privacy/me", headers=headers)).json()["erased"]
    assert (await client.get("/auth/me", headers=headers)).status_code == 401  # account erased
    async with maker()() as db:
        u = (await db.execute(User.__table__.select())).first()
        assert u.email.endswith("@erased.invalid")


async def test_admin_review_queue_and_roles(client, auth):
    headers, s = await start(client, auth)
    await client.post(f"/sessions/{s['id']}/research", json={}, headers=headers)
    assert (await client.get("/admin/review-queue", headers=headers)).status_code == 403  # citizen
    async with maker()() as db:
        u = (await db.execute(User.__table__.select())).first()
        from app.db.models import User as U
        user = await db.get(U, u.id)
        user.role = "reviewer"
        await db.commit()
    login = await client.post("/auth/login", json={"email": "a@example.com", "password": "correct-horse-battery"})
    rh = {"Authorization": f"Bearer {login.json()['access_token']}"}
    q = (await client.get("/admin/review-queue", headers=rh)).json()
    assert q and q[0]["claim"]["source_url"]
    res = await client.post(f"/admin/review-queue/{q[0]['id']}/resolve", json={"status": "verified", "resolution": "Checked on portal"}, headers=rh)
    assert res.status_code == 200
    assert (await client.get("/admin/audit/verify", headers=rh)).json()["chain_valid"]
    assert (await client.post("/admin/refresh", headers=rh)).status_code == 403  # admin only
    assert (await client.post("/admin/review-queue/nope/resolve", json={"status": "verified", "resolution": "xxx"}, headers=rh)).status_code == 404


async def test_admin_actions(client, auth):
    headers, _ = auth
    async with maker()() as db:
        u = (await db.execute(User.__table__.select())).first()
        user = await db.get(User, u.id)
        user.role = "admin"
        await db.commit()
    ah = {"Authorization": f"Bearer {(await client.post('/auth/login', json={'email': 'a@example.com', 'password': 'correct-horse-battery'})).json()['access_token']}"}
    assert (await client.post("/admin/purge", headers=ah)).json()["purged_sessions"] == 0
    assert (await client.post(f"/admin/users/{u.id}/role?role=csc_operator", headers=ah)).json()["role"] == "csc_operator"
    assert (await client.post(f"/admin/users/{u.id}/role?role=root", headers=ah)).status_code in (403, 422)


async def test_reminder_dispatch_uses_labelled_mock(client):
    from datetime import UTC, datetime, timedelta

    async with maker()() as db:
        u = User(email="r@example.com", password_hash="x")
        db.add(u)
        await db.commit()
        from app.db.models import NavSession
        ns = NavSession(user_id=u.id, goal="g")
        db.add(ns)
        from app.db.models import Consent
        db.add(Consent(user_id=u.id, purpose="reminders", policy_version="1.0", granted=True))
        await db.commit()
        db.add_all([
            Reminder(session_id=ns.id, user_id=u.id, title="due", due_at=datetime.now(UTC) - timedelta(hours=1), channel="email", destination="r@example.com"),
            Reminder(session_id=ns.id, user_id=u.id, title="later", due_at=datetime.now(UTC) + timedelta(days=5), channel="email", destination="r@example.com"),
        ])
        await db.commit()
        MockMessenger.OUTBOX.clear()
        integ = get_integrations()
        assert integ.mode == "mock"
        assert await dispatch_due(db, integ) == 1
        assert "not legal advice" in MockMessenger.OUTBOX[0]["text"]


def test_no_code_path_submits_to_government_portal():
    """Static guard: no function/route that submits, and no HTTP POST/PUT to portals from the agent or integrations."""
    root = pathlib.Path(__file__).resolve().parents[1] / "app"
    banned_defs = re.compile(r"def\s+(submit_to|auto_submit|submit_application|file_application|post_to_portal)\w*", re.I)
    for f in root.rglob("*.py"):
        text = f.read_text(encoding="utf-8")
        assert not banned_defs.search(text), f"submission capability in {f}"
    for sub in ("scraping", "agent", "integrations"):
        for f in (root / sub).rglob("*.py"):
            text = f.read_text(encoding="utf-8")
            assert not re.search(r"\.(post|put|patch|delete)\(\s*(url|cur)", text), f"write request to portal in {f}"
    from app.main import app

    routes = set(app.openapi()["paths"])
    assert not [p for p in routes if re.search(r"submit(?!ted)", p)], "no submit route may exist"
    # the only 'submitted' route records the citizen's own statement and requires review
    assert "/sessions/{sid}/submitted" in routes


async def test_withdrawn_reminder_consent_stops_delivery(client, auth):
    from datetime import UTC, datetime, timedelta

    headers, _ = auth
    h, s = await start(client, auth)
    await client.post("/consent", json={"purpose": "reminders", "granted": True}, headers=h)
    async with maker()() as db:
        uid = (await db.execute(User.__table__.select())).first().id
        db.add(Reminder(session_id=s["id"], user_id=uid, title="due", due_at=datetime.now(UTC) - timedelta(hours=1), channel="email", destination="a@example.com"))
        await db.commit()
    await client.post("/consent", json={"purpose": "reminders", "granted": False}, headers=h)
    async with maker()() as db:
        MockMessenger.OUTBOX.clear()
        assert await dispatch_due(db, get_integrations()) == 0
        assert MockMessenger.OUTBOX == []


async def test_login_unknown_email_costs_same_and_fails(client):
    r = await client.post("/auth/login", json={"email": "nobody@example.com", "password": "whatever-long-1"})
    assert r.status_code == 401 and r.json()["detail"] == "Invalid credentials"


async def test_admin_stats_and_users_are_aggregate_and_role_gated(client, auth):
    headers, s = await start(client, auth)
    await client.post(f"/sessions/{s['id']}/research", json={}, headers=headers)
    assert (await client.get("/admin/stats", headers=headers)).status_code == 403  # citizen
    assert (await client.get("/admin/users", headers=headers)).status_code == 403
    async with maker()() as db:
        u = (await db.execute(User.__table__.select())).first()
        (await db.get(User, u.id)).role = "admin"
        await db.commit()
    ah = {"Authorization": f"Bearer {(await client.post('/auth/login', json={'email': 'a@example.com', 'password': 'correct-horse-battery'})).json()['access_token']}"}
    st = (await client.get("/admin/stats", headers=ah)).json()
    assert st["users"]["total"] == 1 and st["sessions"]["total"] == 1
    assert st["knowledge_base"]["claims"] > 0 and "a@example.com" not in str(st)
    assert [x["email"] for x in (await client.get("/admin/users", headers=ah)).json()] == ["a@example.com"]


async def test_create_admin_script(client, monkeypatch):
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("create_admin", Path(__file__).resolve().parents[2] / "scripts" / "create_admin.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert await mod.main("boss@dept.gov.in", "citizen", "long-enough-password") == 2
    assert await mod.main("boss@dept.gov.in", "admin", "short") == 2
    assert await mod.main("Boss@Dept.gov.in", "admin", "long-enough-password") == 0
    assert await mod.main("boss@dept.gov.in", "reviewer", "another-long-password") == 0  # promote/reset, no duplicate
    login = await client.post("/auth/login", json={"email": "boss@dept.gov.in", "password": "another-long-password"})
    assert login.status_code == 200
    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {login.json()['access_token']}"})
    assert me.json()["role"] == "reviewer"


async def test_common_business_types_are_recognised_directly(client, auth):
    headers, _ = auth
    await client.post("/consent", json={"purpose": "service", "granted": True}, headers=headers)
    for goal, activity in [
        ("I want to open a shop in Kolkata", "retail_shop"),
        ("I want to start a gym in Pune", "fitness_centre"),
        ("I want to start an online business in Delhi", "online_seller"),
        ("I want to open a catering service in Chennai", "catering"),
    ]:
        s = (await client.post("/sessions", json={"goal": goal, "language": "en"}, headers=headers)).json()
        assert s["parsed"]["activity"] == activity and not s["parsed"]["clarifying_question"], goal
        r = await client.post(f"/sessions/{s['id']}/research", json={}, headers=headers)
        assert r.status_code == 200 and r.json()["plan"]["steps"], goal


async def test_unrecognised_business_gets_baseline_plan_and_officer_review(client, auth):
    headers, _ = auth
    await client.post("/consent", json={"purpose": "service", "granted": True}, headers=headers)
    s = (await client.post("/sessions", json={"goal": "I want to open an aquarium fish farm in Kolkata", "language": "en"}, headers=headers)).json()
    assert "kind of business" in s["parsed"]["clarifying_question"]
    s2 = (await client.post(f"/sessions/{s['id']}/clarify", json={"answer": "ornamental fish breeding"}, headers=headers)).json()
    assert s2["parsed"]["activity"] == "general_business" and s2["parsed"]["activity_label"] == "ornamental fish breeding"
    assert not s2["parsed"]["clarifying_question"]
    r = await client.post(f"/sessions/{s['id']}/research", json={}, headers=headers)
    assert r.status_code == 200
    plan = r.json()["plan"]
    assert [x["licence"] for x in plan["steps"]][0] == "udyam" and "ornamental fish breeding" in plan["note"]
    r2 = await client.post(f"/sessions/{s['id']}/research", json={}, headers=headers)  # idempotent: one review item
    assert r2.status_code == 200
    from sqlalchemy import select

    from app.db.models import ReviewItem
    async with maker()() as db:
        items = (await db.execute(select(ReviewItem).where(ReviewItem.session_id == s["id"], ReviewItem.claim_id.is_(None)))).scalars().all()
    assert len(items) == 1 and "ornamental fish breeding" in items[0].reason


async def test_non_business_goals_are_escalated_not_forced_into_a_shop_checklist(client, auth):
    headers, _ = auth
    await client.post("/consent", json={"purpose": "service", "granted": True}, headers=headers)
    for goal, intent in [
        ("I want to apply for an agricultural subsidy in Pune", "agri_grant"),
        ("I need a building permit for a house extension in Delhi", "building_permit"),
    ]:
        s = (await client.post("/sessions", json={"goal": goal, "language": "en"}, headers=headers)).json()
        assert s["parsed"]["intent"] == intent and s["parsed"]["activity"] is None and not s["parsed"]["clarifying_question"], goal
        r = await client.post(f"/sessions/{s['id']}/research", json={}, headers=headers)
        assert r.status_code == 200
        plan = r.json()["plan"]
        assert plan["steps"] == [] and plan["out_of_scope"] and "officer" in plan["note"]
        assert r.json()["escalation"]["available"]
    # location is still asked for first
    s = (await client.post("/sessions", json={"goal": "I want a farming grant", "language": "en"}, headers=headers)).json()
    assert "city" in s["parsed"]["clarifying_question"].lower()
