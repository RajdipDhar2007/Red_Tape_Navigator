from datetime import UTC, datetime, timedelta

from app.db.models import User
from app.db.session import maker
from tests.test_api_flow import ANSWERS, start

PW = "correct-horse-battery"


async def _login(client, password=PW):
    return await client.post("/auth/login", json={"email": "a@example.com", "password": password})


async def test_account_locks_after_repeated_failures_and_reset_unlocks(client, auth):
    for _ in range(5):
        assert (await _login(client, "wrong-password-1")).status_code == 401
    locked = await _login(client)  # even the right password is refused while locked
    assert locked.status_code == 429 and locked.json()["detail"]["code"] == "account_locked"

    from app.integrations.mock import MockMessenger

    MockMessenger.OUTBOX.clear()
    await client.post("/auth/forgot", json={"email": "a@example.com"})
    import re

    token = re.search(r"token=([\w.\-]+)", MockMessenger.OUTBOX[-1]["text"]).group(1)  # type: ignore[union-attr]
    assert (await client.post("/auth/reset", json={"token": token, "password": "a-brand-new-passphrase"})).status_code == 200
    assert (await _login(client, "a-brand-new-passphrase")).status_code == 200


async def test_lock_expires_and_success_resets_counter(client, auth):
    for _ in range(4):
        await _login(client, "wrong-password-1")
    assert (await _login(client)).status_code == 200  # 4 failures < threshold; success clears the counter
    for _ in range(5):
        await _login(client, "wrong-password-1")
    assert (await _login(client)).status_code == 429
    async with maker()() as db:
        u = (await db.execute(User.__table__.select())).first()
        user = await db.get(User, u.id)
        assert user is not None
        user.locked_until = datetime.now(UTC) - timedelta(minutes=1)
        await db.commit()
    assert (await _login(client)).status_code == 200


async def test_unknown_email_failures_do_not_lock_or_leak(client):
    for _ in range(7):
        r = await client.post("/auth/login", json={"email": "nobody@example.com", "password": "whatever-123456"})
        assert r.status_code == 401


async def test_dashboard_lists_only_own_applications(client, auth):
    headers, s = await start(client, auth, "I want to open a small bakery in Kolkata")
    await client.post(f"/sessions/{s['id']}/research", json={}, headers=headers)
    rows = (await client.get("/sessions", headers=headers)).json()
    assert len(rows) == 1 and rows[0]["id"] == s["id"] and rows[0]["activity"] == "bakery" and rows[0]["steps"] >= 4
    assert rows[0]["reviewed"] is False
    other = (await client.post("/auth/register", json={"email": "b@example.com", "password": PW})).json()
    assert (await client.get("/sessions", headers={"Authorization": f"Bearer {other['access_token']}"})).json() == []
    assert (await client.get("/sessions")).status_code == 401


async def test_keyin_sheet_needs_review_and_returns_real_values(client, auth):
    headers, s = await start(client, auth)
    sid = s["id"]
    await client.post(f"/sessions/{sid}/research", json={}, headers=headers)
    for _ in range(40):
        st = (await client.get(f"/sessions/{sid}/interview", headers=headers)).json()
        if not st["questions"]:
            break
        keys = [q["key"] for q in st["questions"]]
        await client.post(f"/sessions/{sid}/interview", json={"answers": {k: ANSWERS[k] for k in keys}}, headers=headers)
    assert (await client.get(f"/sessions/{sid}/forms/udyam_details/keyin", headers=headers)).status_code == 403  # not reviewed yet
    assert (await client.post(f"/sessions/{sid}/review", json={"confirm": True}, headers=headers)).status_code == 200
    k = await client.get(f"/sessions/{sid}/forms/udyam_details/keyin", headers=headers)
    assert k.status_code == 200
    body = k.json()
    assert body["portal_url"].startswith("https://") and "never submits" in body["important"]
    vals = {r["label"]: r["value"] for r in body["rows"]}
    assert ANSWERS["applicant_name"].upper() in vals.values()  # formatted as the form requires
    assert ANSWERS["aadhaar"].replace(" ", "") in "".join(v.replace(" ", "") for v in vals.values())  # real, unmasked, so it can be pasted
    assert (await client.get(f"/sessions/{sid}/forms/nope/keyin", headers=headers)).status_code == 404
    other = (await client.post("/auth/register", json={"email": "c@example.com", "password": PW})).json()
    assert (await client.get(f"/sessions/{sid}/forms/udyam_details/keyin", headers={"Authorization": f"Bearer {other['access_token']}"})).status_code == 404
