import time

from sqlalchemy import select, update

from app.core import totp
from app.core.security import create_verify_token
from app.db.models import AuditLog, User, WorkspaceInvite
from app.db.session import maker

PW = "correct-horse-battery"


async def _register(client, email):
    r = await client.post("/auth/register", json={"email": email, "password": PW})
    assert r.status_code == 201
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    uid = (await client.get("/auth/me", headers=h)).json()["id"]
    return h, uid


async def _verify(client, uid, email):
    r = await client.post("/auth/verify-email", json={"token": create_verify_token(uid, email)})
    assert r.status_code == 200


def test_totp_matches_rfc6238_vectors_and_blocks_replay():
    secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"  # ASCII "12345678901234567890", the RFC 6238 SHA-1 test key
    assert totp.code_at(secret, 59 // 30) == "287082"  # RFC 6238 appendix B, T=59 (last six digits of 94287082)
    assert totp.code_at(secret, 1111111109 // 30) == "081804"
    step = totp.verify(secret, "287082", 0, now=59)
    assert step == 1
    assert totp.verify(secret, "287082", step, now=59) is None  # same code cannot be used twice
    assert totp.verify(secret, "000000", 0, now=59) is None and totp.verify(secret, "abc", 0, now=59) is None
    assert totp.otpauth_uri(secret, "a@b.in").startswith("otpauth://totp/Red%20Tape%20Navigator:a%40b.in?secret=")


async def test_email_verification_flow(client):
    h, uid = await _register(client, "v@example.com")
    assert (await client.get("/auth/me", headers=h)).json()["email_verified"] is False
    assert (await client.post("/auth/verify-email", json={"token": "x" * 30})).status_code == 400
    wrong = create_verify_token(uid, "someone-else@example.com")  # bound to an address that is not the account's
    assert (await client.post("/auth/verify-email", json={"token": wrong})).status_code == 400
    assert (await client.post("/auth/verify-email/send", headers=h)).status_code == 202
    await _verify(client, uid, "v@example.com")
    assert (await client.get("/auth/me", headers=h)).json()["email_verified"] is True


async def test_two_factor_enrol_login_recovery_and_disable(client):
    h, uid = await _register(client, "t@example.com")
    assert (await client.post("/auth/2fa/enable", json={"code": "123456"}, headers=h)).status_code == 409  # no setup yet
    secret = (await client.post("/auth/2fa/setup", headers=h)).json()["secret"]
    bad = await client.post("/auth/2fa/enable", json={"code": "000000"}, headers=h)
    assert bad.status_code == 400
    now_step = int(time.time() // 30)
    en = await client.post("/auth/2fa/enable", json={"code": totp.code_at(secret, now_step)}, headers=h)
    assert en.status_code == 200 and len(en.json()["recovery_codes"]) == 8
    codes = en.json()["recovery_codes"]
    assert (await client.post("/auth/2fa/setup", headers=h)).status_code == 409
    async with maker()() as db:  # the secret is stored encrypted, recovery codes only as hashes
        u = await db.get(User, uid)
        assert u.totp_secret and secret not in u.totp_secret and all(c not in str(u.recovery_hashes) for c in codes)

    login = {"email": "t@example.com", "password": PW}
    need = await client.post("/auth/login", json=login)
    assert need.status_code == 401 and need.json()["detail"]["code"] == "otp_required"
    assert (await client.post("/auth/login", json={**login, "otp": "000000"})).status_code == 401
    assert (await client.post("/auth/login", json={**login, "password": "wrong-password-here", "otp": codes[0]})).status_code == 401
    # a code that was used to enable cannot be replayed to sign in
    assert (await client.post("/auth/login", json={**login, "otp": totp.code_at(secret, now_step)})).status_code == 401
    ok = await client.post("/auth/login", json={**login, "otp": totp.code_at(secret, now_step + 1)})
    assert ok.status_code == 200
    rec = await client.post("/auth/login", json={**login, "otp": codes[0]})
    assert rec.status_code == 200
    assert (await client.post("/auth/login", json={**login, "otp": codes[0]})).status_code == 401  # recovery code is single-use
    assert (await client.get("/auth/me", headers=h)).json()["two_factor"] is True

    h2 = {"Authorization": f"Bearer {rec.json()['access_token']}"}
    assert (await client.post("/auth/2fa/disable", json={"password": "nope-nope-nope", "code": codes[1]}, headers=h2)).status_code == 403
    off = await client.post("/auth/2fa/disable", json={"password": PW, "code": codes[1]}, headers=h2)
    assert off.status_code == 200
    assert (await client.post("/auth/login", json=login)).status_code == 200  # no second factor any more
    assert (await client.post("/auth/2fa/disable", json={"password": PW, "code": "123456"}, headers=h2)).status_code == 409


async def test_wrong_codes_count_toward_lockout(client):
    h, _ = await _register(client, "l@example.com")
    secret = (await client.post("/auth/2fa/setup", headers=h)).json()["secret"]
    await client.post("/auth/2fa/enable", json={"code": totp.code_at(secret, int(time.time() // 30))}, headers=h)
    login = {"email": "l@example.com", "password": PW}
    from app.core.config import get_settings

    for _ in range(get_settings().lockout_threshold):
        await client.post("/auth/login", json={**login, "otp": "111111"})
    locked = await client.post("/auth/login", json={**login, "otp": "111111"})
    assert locked.status_code == 429


async def test_workspace_lifecycle_invites_roles_and_sharing(client):
    owner, oid = await _register(client, "o@example.com")
    guest, gid = await _register(client, "g@example.com")
    outsider, _ = await _register(client, "x@example.com")

    ws = (await client.post("/workspaces", json={"name": "Dhar Sweets"}, headers=owner)).json()
    wid = ws["id"]
    assert ws["role"] == "owner"
    assert (await client.get(f"/workspaces/{wid}", headers=outsider)).status_code == 404  # existence is not revealed

    # inviting needs a verified email
    assert (await client.post(f"/workspaces/{wid}/invites", json={"email": "g@example.com"}, headers=owner)).status_code == 403
    await _verify(client, oid, "o@example.com")
    assert (await client.post(f"/workspaces/{wid}/invites", json={"email": "g@example.com", "role": "owner"}, headers=owner)).status_code == 422
    inv = (await client.post(f"/workspaces/{wid}/invites", json={"email": "G@Example.com", "role": "member"}, headers=owner)).json()
    assert inv["email"] == "g@example.com" and len(inv["token"]) >= 30
    async with maker()() as db:  # only a hash is stored
        row = (await db.execute(select(WorkspaceInvite))).scalars().one()
        assert inv["token"] not in (row.token_hash + row.email)
    assert len((await client.get(f"/workspaces/{wid}/invites", headers=owner)).json()) == 1
    assert (await client.get(f"/workspaces/{wid}/invites", headers=guest)).status_code == 404

    # accept: wrong person, unverified person, then the right one
    assert (await client.post("/workspaces/invites/accept", json={"token": inv["token"]}, headers=outsider)).status_code == 400
    assert (await client.post("/workspaces/invites/accept", json={"token": inv["token"]}, headers=guest)).status_code == 403
    await _verify(client, gid, "g@example.com")
    assert (await client.post("/workspaces/invites/accept", json={"token": "z" * 40}, headers=guest)).status_code == 400
    joined = await client.post("/workspaces/invites/accept", json={"token": inv["token"]}, headers=guest)
    assert joined.status_code == 200 and joined.json()["role"] == "member"
    assert (await client.post("/workspaces/invites/accept", json={"token": inv["token"]}, headers=guest)).status_code == 400  # used once

    detail = (await client.get(f"/workspaces/{wid}", headers=guest)).json()
    assert detail["your_role"] == "member" and {m["email"] for m in detail["members"]} == {"o@example.com", "g@example.com"}
    assert [w["id"] for w in (await client.get("/workspaces", headers=guest)).json()] == [wid]

    # sessions: private until shared, then every member can open them
    sid = await _session(client, owner)
    assert (await client.get(f"/sessions/{sid}", headers=guest)).status_code == 404
    assert (await client.post(f"/workspaces/{wid}/sessions", json={"session_id": sid}, headers=guest)).status_code == 404  # not theirs
    assert (await client.post(f"/workspaces/{wid}/sessions", json={"session_id": sid}, headers=owner)).status_code == 201
    assert (await client.get(f"/sessions/{sid}", headers=guest)).status_code == 200
    assert (await client.get(f"/sessions/{sid}", headers=outsider)).status_code == 404
    listed = (await client.get(f"/workspaces/{wid}/sessions", headers=guest)).json()
    assert [s["id"] for s in listed] == [sid] and listed[0]["owner"] == "o@example.com"
    assert (await client.delete(f"/workspaces/{wid}/sessions/{sid}", headers=guest)).status_code == 403  # member, not the owner
    assert (await client.delete(f"/workspaces/{wid}/sessions/{sid}", headers=owner)).status_code == 204
    assert (await client.get(f"/sessions/{sid}", headers=guest)).status_code == 404

    # roles and removal
    assert (await client.patch(f"/workspaces/{wid}/members/{gid}", json={"role": "admin"}, headers=guest)).status_code == 403
    assert (await client.patch(f"/workspaces/{wid}/members/{gid}", json={"role": "admin"}, headers=owner)).status_code == 200
    assert (await client.patch(f"/workspaces/{wid}/members/{oid}", json={"role": "member"}, headers=owner)).status_code == 409
    assert (await client.delete(f"/workspaces/{wid}/members/{oid}", headers=guest)).status_code == 409  # owner cannot be removed
    await client.post(f"/workspaces/{wid}/sessions", json={"session_id": sid}, headers=owner)
    assert (await client.delete(f"/workspaces/{wid}/members/{gid}", headers=guest)).status_code == 204  # leaving
    assert (await client.get(f"/workspaces/{wid}", headers=guest)).status_code == 404

    # deleting the workspace unshares, never deletes, sessions
    assert (await client.delete(f"/workspaces/{wid}", headers=guest)).status_code == 404
    assert (await client.delete(f"/workspaces/{wid}", headers=owner)).status_code == 204
    assert (await client.get(f"/sessions/{sid}", headers=owner)).status_code == 200
    assert (await client.get("/workspaces", headers=owner)).json() == []
    async with maker()() as db:
        actions = {a for (a,) in (await db.execute(select(AuditLog.action))).all()}
    assert {"workspace.created", "workspace.invite_created", "workspace.joined", "workspace.session_shared"} <= actions


async def test_expired_invite_and_admin_limits(client):
    owner, oid = await _register(client, "o2@example.com")
    adm, aid = await _register(client, "a2@example.com")
    mem, mid = await _register(client, "m2@example.com")
    for h, uid, em in ((owner, oid, "o2@example.com"), (adm, aid, "a2@example.com"), (mem, mid, "m2@example.com")):
        await _verify(client, uid, em)
    wid = (await client.post("/workspaces", json={"name": "Firm"}, headers=owner)).json()["id"]
    for em, h, role in (("a2@example.com", adm, "admin"), ("m2@example.com", mem, "member")):
        t = (await client.post(f"/workspaces/{wid}/invites", json={"email": em, "role": role}, headers=owner)).json()["token"]
        assert (await client.post("/workspaces/invites/accept", json={"token": t}, headers=h)).status_code == 200
    # an admin can invite and remove members but not other admins or the owner
    assert (await client.post(f"/workspaces/{wid}/invites", json={"email": "n@example.com"}, headers=adm)).status_code == 201
    assert (await client.delete(f"/workspaces/{wid}/members/{oid}", headers=adm)).status_code == 409
    assert (await client.delete(f"/workspaces/{wid}/members/{mid}", headers=adm)).status_code == 204
    assert (await client.delete(f"/workspaces/{wid}/members/{aid}", headers=mem)).status_code == 404  # no longer a member
    # expiry
    t = (await client.post(f"/workspaces/{wid}/invites", json={"email": "m2@example.com"}, headers=owner)).json()["token"]
    async with maker()() as db:
        from datetime import UTC, datetime, timedelta

        await db.execute(update(WorkspaceInvite).values(expires_at=datetime.now(UTC) - timedelta(days=1)))
        await db.commit()
    assert (await client.post("/workspaces/invites/accept", json={"token": t}, headers=mem)).status_code == 400
    invs = (await client.get(f"/workspaces/{wid}/invites", headers=owner)).json()
    assert invs and all(i["expired"] for i in invs)
    iid = invs[0]["id"]
    assert (await client.delete(f"/workspaces/{wid}/invites/{iid}", headers=owner)).status_code == 204
    assert (await client.delete(f"/workspaces/{wid}/invites/{iid}", headers=owner)).status_code == 404


async def test_erasing_an_account_hands_over_or_removes_its_workspaces(client):
    owner, oid = await _register(client, "e1@example.com")
    other, otid = await _register(client, "e2@example.com")
    await _verify(client, oid, "e1@example.com")
    await _verify(client, otid, "e2@example.com")
    wid = (await client.post("/workspaces", json={"name": "Shared"}, headers=owner)).json()["id"]
    solo = (await client.post("/workspaces", json={"name": "Solo"}, headers=owner)).json()["id"]
    t = (await client.post(f"/workspaces/{wid}/invites", json={"email": "e2@example.com"}, headers=owner)).json()["token"]
    await client.post("/workspaces/invites/accept", json={"token": t}, headers=other)
    exp = (await client.get("/privacy/export", headers=owner)).json()
    assert {w["name"] for w in exp["workspaces"]} == {"Shared", "Solo"}
    assert (await client.request("DELETE", "/privacy/me", headers=owner)).status_code == 200
    assert (await client.get(f"/workspaces/{wid}", headers=other)).json()["your_role"] == "owner"  # handed over
    async with maker()() as db:
        from app.db.models import Workspace

        assert await db.get(Workspace, solo) is None  # nobody else was in it


async def _session(client, headers):
    assert (await client.post("/consent", json={"purpose": "service", "granted": True}, headers=headers)).status_code in (200, 201)
    r = await client.post("/sessions", json={"goal": "I want to open a small bakery in Kolkata", "language": "en"}, headers=headers)
    assert r.status_code == 201
    return r.json()["id"]
