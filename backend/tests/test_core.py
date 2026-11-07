import pytest
from sqlalchemy import update

from app.core import audit
from app.core.crypto import decrypt, encrypt, mask, redact
from app.db.models import AuditLog
from app.db.session import maker


def test_crypto_roundtrip_and_redaction():
    assert decrypt(encrypt("ABCDE1234F")) == "ABCDE1234F"
    assert encrypt("x") != "x"
    assert mask("123456789012") == "********9012"
    out = redact({"pan": "ABCDE1234F", "note": "aadhaar 1234 5678 9012 and ABCDE1234F"})
    assert out["pan"] == "[REDACTED]"
    assert "1234 5678 9012" not in out["note"] and "ABCDE1234F" not in out["note"]


async def test_register_login_refresh_rotation(client):
    r = await client.post("/auth/register", json={"email": "u@example.com", "password": "long-enough-pass"})
    assert r.status_code == 201
    assert (await client.post("/auth/register", json={"email": "u@example.com", "password": "long-enough-pass"})).status_code == 409
    toks = (await client.post("/auth/login", json={"email": "u@example.com", "password": "long-enough-pass"})).json()
    assert (await client.post("/auth/login", json={"email": "u@example.com", "password": "wrong-password"})).status_code == 401
    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {toks['access_token']}"})
    assert me.json()["role"] == "citizen"
    new = await client.post("/auth/refresh", json={"refresh_token": toks["refresh_token"]})
    assert new.status_code == 200
    # reuse of old refresh token is rejected and revokes the family
    assert (await client.post("/auth/refresh", json={"refresh_token": toks["refresh_token"]})).status_code == 401
    assert (await client.post("/auth/refresh", json={"refresh_token": new.json()["refresh_token"]})).status_code == 401
    # access token can't be used as a refresh token
    assert (await client.post("/auth/refresh", json={"refresh_token": toks["access_token"]})).status_code == 401


async def test_auth_required(client):
    assert (await client.get("/auth/me")).status_code == 401
    assert (await client.get("/auth/me", headers={"Authorization": "Bearer junk"})).status_code == 401


async def test_consent_flow(client, auth):
    headers, _ = auth
    assert (await client.get("/consent/notice")).json()["policy_version"]
    assert (await client.post("/consent", json={"purpose": "service", "granted": True}, headers=headers)).status_code == 201
    assert (await client.post("/consent", json={"purpose": "bogus", "granted": True}, headers=headers)).status_code == 422
    await client.post("/consent", json={"purpose": "service", "granted": False}, headers=headers)
    log = (await client.get("/consent", headers=headers)).json()
    assert [c["granted"] for c in log] == [True, False]


async def test_audit_chain_and_immutability(client, auth):
    async with maker()() as db:
        await audit.record(db, "tester", "x.y", {"pan": "ABCDE1234F"})
        assert await audit.verify_chain(db)
        row = (await db.execute(AuditLog.__table__.select().where(AuditLog.action == "x.y"))).first()
        assert "ABCDE1234F" not in str(row.detail)
        with pytest.raises(PermissionError):
            obj = await db.get(AuditLog, row.seq)
            obj.action = "tampered"
            await db.commit()
        await db.rollback()
        # tamper at SQL level -> chain verification fails
        await db.execute(update(AuditLog).where(AuditLog.seq == row.seq).values(action="tampered"))
        await db.commit()
        assert not await audit.verify_chain(db)
