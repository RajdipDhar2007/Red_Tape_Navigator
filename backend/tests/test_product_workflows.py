"""End-to-end product workflow tests for Journey A (New User), Session Management, Reminders Lifecycle, and Policy Facts."""

from httpx import AsyncClient

PW = "CorrectHorse99!"


async def _register_and_headers(client: AsyncClient, email: str) -> dict[str, str]:
    r = await client.post("/auth/register", json={"email": email, "password": PW, "language": "en"})
    assert r.status_code == 201, r.text
    tok = r.json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


async def test_full_end_to_end_journey_session_rename_and_reminders_lifecycle(client: AsyncClient):
    h1 = await _register_and_headers(client, "journey-owner@example.com")
    h2 = await _register_and_headers(client, "journey-other@example.com")

    # 1. Grant service and reminders consent
    for purpose in ("service", "reminders"):
        rc = await client.post("/consent", headers=h1, json={"purpose": purpose, "granted": True})
        assert rc.status_code == 201
    for purpose in ("service", "reminders"):
        rc = await client.post("/consent", headers=h2, json={"purpose": purpose, "granted": True})
        assert rc.status_code == 201

    # 2. Create session (Journey A intake)
    rs = await client.post(
        "/sessions",
        headers=h1,
        json={"goal": "I want to open a small bakery in Pune", "language": "en"},
    )
    assert rs.status_code == 201, rs.text
    sid = rs.json()["id"]
    assert rs.json()["tracker"]["current"] in ("research", "checklist")

    # 3. Run research to generate personalized plan & checklist
    rr = await client.post(f"/sessions/{sid}/research", headers=h1, json={"live": False})
    assert rr.status_code == 200, rr.text
    steps = rr.json()["plan"]["steps"]
    assert len(steps) >= 1

    # 4. Inspect checklist
    rchk = await client.get(f"/sessions/{sid}/checklist", headers=h1)
    assert rchk.status_code == 200
    assert len(rchk.json()["plan"]["steps"]) == len(steps)

    # 5. Rename session title (PATCH /sessions/{sid}) and verify validation + ownership
    r_short = await client.patch(f"/sessions/{sid}", headers=h1, json={"goal": "   abc   "})
    assert r_short.status_code == 422

    r_other_rename = await client.patch(
        f"/sessions/{sid}",
        headers=h2,
        json={"goal": "Unauthorized rename attempt"},
    )
    assert r_other_rename.status_code == 404

    new_title = "Sunrise Bakery - Pune Kothrud Branch"
    r_rename = await client.patch(f"/sessions/{sid}", headers=h1, json={"goal": new_title})
    assert r_rename.status_code == 200, r_rename.text
    assert r_rename.json()["goal"] == new_title
    # Parsed activity and city are preserved when renaming display title
    assert r_rename.json()["parsed"]["city"] == "Pune"

    # 6. Verify GET /sessions returns updated goal and current stage
    r_list = await client.get("/sessions", headers=h1)
    assert r_list.status_code == 200
    listed = next(x for x in r_list.json() if x["id"] == sid)
    assert listed["goal"] == new_title
    assert "stage" in listed

    # 7. Interview state & skipping/answering
    rint = await client.get(f"/sessions/{sid}/interview", headers=h1)
    assert rint.status_code == 200

    # 8. Review & confirm (acknowledging any incomplete optional fields)
    rrev = await client.get(f"/sessions/{sid}/review", headers=h1)
    assert rrev.status_code == 200
    forms = rrev.json()["forms"]
    assert len(forms) >= 1
    first_form_id = forms[0]["form_id"]

    rconf = await client.post(
        f"/sessions/{sid}/review",
        headers=h1,
        json={"confirm": True, "acknowledge_incomplete": True},
    )
    assert rconf.status_code == 200
    assert rconf.json()["reviewed"] is True

    # 9. Download PDF, Key-in sheet, and Submission checklist
    rpdf = await client.get(f"/sessions/{sid}/forms/{first_form_id}/download", headers=h1)
    assert rpdf.status_code == 200
    assert rpdf.headers["content-type"] == "application/pdf"

    rkeyin = await client.get(f"/sessions/{sid}/forms/{first_form_id}/keyin", headers=h1)
    assert rkeyin.status_code == 200
    assert rkeyin.json()["form_id"] == first_form_id

    rsub_chk = await client.get(f"/sessions/{sid}/submission-checklist", headers=h1)
    assert rsub_chk.status_code == 200
    first_licence = rsub_chk.json()["items"][0]["licence"]

    # 10. Reminders lifecycle: empty list -> schedule -> list -> cancel -> verify removed
    rrem0 = await client.get(f"/sessions/{sid}/reminders", headers=h1)
    assert rrem0.status_code == 200
    assert rrem0.json()["items"] == []
    assert "email" in rrem0.json()["channels"]

    rsched = await client.post(
        f"/sessions/{sid}/submitted",
        headers=h1,
        json={"licences": [first_licence], "channel": "email"},
    )
    assert rsched.status_code == 200, rsched.text
    scheduled = rsched.json()["scheduled"]
    assert len(scheduled) >= 1
    assert scheduled[0]["status"] == "scheduled"
    assert scheduled[0]["delivery_mode"] in ("live", "mock")
    rid = scheduled[0]["id"]

    # Reopen reminders via GET /sessions/{sid}/reminders
    rrem1 = await client.get(f"/sessions/{sid}/reminders", headers=h1)
    assert rrem1.status_code == 200
    items = rrem1.json()["items"]
    assert any(x["id"] == rid for x in items)

    # Other user cannot list or cancel reminders for this session
    assert (await client.get(f"/sessions/{sid}/reminders", headers=h2)).status_code == 404
    assert (await client.delete(f"/sessions/{sid}/reminders/{rid}", headers=h2)).status_code == 404

    # Owner cancels the reminder
    rdel = await client.delete(f"/sessions/{sid}/reminders/{rid}", headers=h1)
    assert rdel.status_code == 204

    # Deleting again returns 404
    assert (await client.delete(f"/sessions/{sid}/reminders/{rid}", headers=h1)).status_code == 404

    # Verify removed from list
    rrem2 = await client.get(f"/sessions/{sid}/reminders", headers=h1)
    assert rrem2.status_code == 200
    assert not any(x["id"] == rid for x in rrem2.json()["items"])


async def test_help_centre_policy_facts_endpoint_returns_live_configuration(client: AsyncClient):
    r = await client.get("/privacy/policy")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["retention_days"], int)
    assert isinstance(body["data_region"], str)
    assert isinstance(body["grievance_contact"], str)
