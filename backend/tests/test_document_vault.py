"""Comprehensive security, ownership, storage, malware-scanning, and DPDP privacy tests for the Document Vault."""
import hashlib

import httpx
import pytest
from sqlalchemy import select

from app.core import config
from app.core.scanner import ExternalHttpMalwareScanner, set_scanner_override
from app.core.security import create_verify_token
from app.core.storage import (
    LocalStorageBackend,
    ObjectNotFoundError,
    S3StorageBackend,
    StorageError,
    get_storage,
    set_storage_override,
    validate_object_key,
)
from app.db.models import Document
from app.db.session import maker

PW = "correct-horse-battery"
VALID_PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"
VALID_PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
VALID_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"


async def _register_user(client, email: str):
    r = await client.post("/auth/register", json={"email": email, "password": PW})
    assert r.status_code == 201
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    uid = (await client.get("/auth/me", headers=headers)).json()["id"]
    return headers, uid


async def test_upload_security_validation(client):
    # 1. Unauthenticated upload rejected
    r_unauth = await client.post(
        "/documents",
        files={"file": ("doc.pdf", VALID_PDF, "application/pdf")},
    )
    assert r_unauth.status_code == 401

    headers, _ = await _register_user(client, "up@example.com")

    # 2. Unsupported MIME type rejected
    r_bad_mime = await client.post(
        "/documents",
        files={"file": ("script.sh", b"#!/bin/sh\necho hi", "application/x-sh")},
        headers=headers,
    )
    assert r_bad_mime.status_code == 415
    assert r_bad_mime.json()["detail"]["code"] == "unsupported_file_type"

    # 3. Executable double extension rejected even with PDF content and MIME
    r_double_ext = await client.post(
        "/documents",
        files={"file": ("invoice.pdf.exe", VALID_PDF, "application/pdf")},
        headers=headers,
    )
    assert r_double_ext.status_code == 415
    assert r_double_ext.json()["detail"]["code"] == "unsupported_file_type"

    # 4. Extension mismatch rejected (.png filename with application/pdf MIME)
    r_ext_mismatch = await client.post(
        "/documents",
        files={"file": ("photo.png", VALID_PDF, "application/pdf")},
        headers=headers,
    )
    assert r_ext_mismatch.status_code == 415
    assert r_ext_mismatch.json()["detail"]["code"] == "extension_mismatch"

    # 5. Magic-byte signature mismatch rejected (text bytes claiming to be PDF)
    r_bad_magic = await client.post(
        "/documents",
        files={"file": ("fake.pdf", b"not a real pdf file", "application/pdf")},
        headers=headers,
    )
    assert r_bad_magic.status_code == 415
    assert r_bad_magic.json()["detail"]["code"] == "invalid_file_signature"

    # 6. Empty file rejected
    r_empty = await client.post(
        "/documents",
        files={"file": ("empty.pdf", b"", "application/pdf")},
        headers=headers,
    )
    assert r_empty.status_code == 400
    assert r_empty.json()["detail"]["code"] == "empty_file"

    # 7. Valid PDF, PNG, and JPEG accepted with exact SHA-256 checksum
    for fname, payload, ctype, cat in (
        ("rent_agreement.pdf", VALID_PDF, "application/pdf", "premises"),
        ("shop_front.png", VALID_PNG, "image/png", "business"),
        ("pan_card.jpg", VALID_JPEG, "image/jpeg", "identity"),
    ):
        r_ok = await client.post(
            "/documents",
            data={"category": cat},
            files={"file": (fname, payload, ctype)},
            headers=headers,
        )
        assert r_ok.status_code == 201
        body = r_ok.json()
        assert body["original_filename"] == fname
        assert body["content_type"] == ctype
        assert body["size_bytes"] == len(payload)
        assert body["checksum"] == hashlib.sha256(payload).hexdigest()
        assert body["category"] == cat
        assert body["scan_status"] == "disabled"
        assert "stored_object_key" not in body


async def test_oversized_upload_rejected(client, monkeypatch):
    headers, _ = await _register_user(client, "big@example.com")
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "100")
    config.get_settings.cache_clear()
    try:
        oversized_pdf = VALID_PDF + (b"A" * 200)
        r = await client.post(
            "/documents",
            files={"file": ("large.pdf", oversized_pdf, "application/pdf")},
            headers=headers,
        )
        assert r.status_code == 413
        assert r.json()["detail"]["code"] == "file_too_large"
    finally:
        monkeypatch.delenv("MAX_UPLOAD_BYTES", raising=False)
        config.get_settings.cache_clear()


async def test_ownership_isolation_and_workspace_sharing(client):
    h_a, uid_a = await _register_user(client, "alice@example.com")
    h_b, uid_b = await _register_user(client, "bob@example.com")
    h_c, _ = await _register_user(client, "charlie@example.com")

    # Alice uploads a private document
    up = await client.post(
        "/documents",
        files={"file": ("alice_private.pdf", VALID_PDF, "application/pdf")},
        headers=h_a,
    )
    assert up.status_code == 201
    doc_id = up.json()["id"]

    # Bob cannot see Alice's document in his list, metadata, download, or delete
    bob_list = (await client.get("/documents", headers=h_b)).json()
    assert bob_list["items"] == [] and bob_list["total"] == 0
    assert (await client.get(f"/documents/{doc_id}", headers=h_b)).status_code == 404
    assert (await client.get(f"/documents/{doc_id}/download", headers=h_b)).status_code == 404
    assert (await client.delete(f"/documents/{doc_id}", headers=h_b)).status_code == 404

    # Alice can download her own document
    dl = await client.get(f"/documents/{doc_id}/download", headers=h_a)
    assert dl.status_code == 200
    assert dl.content == VALID_PDF
    assert dl.headers["content-type"] == "application/pdf"
    assert 'attachment; filename="alice_private.pdf"' in dl.headers["content-disposition"]

    # Create a workspace with Alice (owner) and Bob (member); Charlie is an outsider
    await client.post("/auth/verify-email", json={"token": create_verify_token(uid_a, "alice@example.com")})
    await client.post("/auth/verify-email", json={"token": create_verify_token(uid_b, "bob@example.com")})
    ws = (await client.post("/workspaces", json={"name": "Shared Firm"}, headers=h_a)).json()
    wid = ws["id"]
    inv = (await client.post(f"/workspaces/{wid}/invites", json={"email": "bob@example.com"}, headers=h_a)).json()
    assert (await client.post("/workspaces/invites/accept", json={"token": inv["token"]}, headers=h_b)).status_code == 200

    # Alice uploads a document shared with the workspace
    ws_up = await client.post(
        "/documents",
        data={"workspace_id": wid, "category": "licence"},
        files={"file": ("shared_cert.pdf", VALID_PDF, "application/pdf")},
        headers=h_a,
    )
    assert ws_up.status_code == 201
    ws_doc_id = ws_up.json()["id"]

    # Bob (workspace member) can list workspace documents, get metadata, and download, but cannot delete Alice's document
    ws_list_b = await client.get(f"/documents?workspace_id={wid}", headers=h_b)
    assert ws_list_b.status_code == 200
    assert [d["id"] for d in ws_list_b.json()["items"]] == [ws_doc_id]
    assert ws_list_b.json()["items"][0]["is_owner"] is False
    assert (await client.get(f"/documents/{ws_doc_id}", headers=h_b)).status_code == 200
    assert (await client.get(f"/documents/{ws_doc_id}/download", headers=h_b)).content == VALID_PDF
    assert (await client.delete(f"/documents/{ws_doc_id}", headers=h_b)).status_code == 404

    # Charlie (outsider) cannot list or access workspace documents
    assert (await client.get(f"/documents?workspace_id={wid}", headers=h_c)).status_code == 404
    assert (await client.get(f"/documents/{ws_doc_id}", headers=h_c)).status_code == 404


async def test_storage_key_safety_path_traversal_and_cleanup(client, tmp_path, monkeypatch):
    headers, uid = await _register_user(client, "sec@example.com")

    # Path traversal in filename is stripped and server-generated storage key is used
    r = await client.post(
        "/documents",
        files={"file": ("../../../../etc/passwd/../../evil..name.pdf", VALID_PDF, "application/pdf")},
        headers=headers,
    )
    assert r.status_code == 201
    doc_id = r.json()["id"]
    assert ".." not in r.json()["original_filename"]
    assert "/" not in r.json()["original_filename"]
    assert "\\" not in r.json()["original_filename"]

    async with maker()() as db:
        doc = await db.get(Document, doc_id)
        assert doc is not None
        assert doc.stored_object_key == f"vault/{uid}/{doc_id}.pdf"
        assert "evil" not in doc.stored_object_key and "passwd" not in doc.stored_object_key

    # Direct LocalStorageBackend path traversal rejection and partial upload cleanup
    local = LocalStorageBackend(tmp_path / "vault")
    for bad_key in ("../escape.pdf", "/abs/path.pdf", "a/../../b.pdf", "bad\\slash.pdf", ""):
        with pytest.raises(StorageError):
            validate_object_key(bad_key)
        with pytest.raises(StorageError):
            await local.put(bad_key, VALID_PDF, "application/pdf")

    # Simulate os.replace failure during LocalStorageBackend.put -> temporary .part-* file is cleaned up
    import os

    def boom_replace(src, dst):
        raise OSError("simulated disk error")

    monkeypatch.setattr(os, "replace", boom_replace)
    with pytest.raises(StorageError):
        await local.put("vault/u1/doc1.pdf", VALID_PDF, "application/pdf")
    part_files = list((tmp_path / "vault").rglob(".part-*"))
    assert part_files == []


async def test_db_failure_cleans_up_uploaded_storage_object(client, monkeypatch):
    headers, _ = await _register_user(client, "orphan@example.com")
    deleted_keys: list[str] = []
    real_storage = get_storage()

    class TrackingStorage:
        async def put(self, key: str, data: bytes, content_type: str) -> None:
            await real_storage.put(key, data, content_type)

        async def get(self, key: str) -> bytes:
            return await real_storage.get(key)

        async def delete(self, key: str) -> None:
            deleted_keys.append(key)
            await real_storage.delete(key)

    set_storage_override(TrackingStorage())
    try:
        from sqlalchemy.ext.asyncio import AsyncSession

        orig_commit = AsyncSession.commit

        async def fail_commit(self):
            # Fail only when Document is in the session's new objects
            if any(isinstance(obj, Document) for obj in self.new):
                raise RuntimeError("simulated db commit failure")
            await orig_commit(self)

        monkeypatch.setattr(AsyncSession, "commit", fail_commit)
        with pytest.raises(RuntimeError, match="simulated db commit failure"):
            await client.post(
                "/documents",
                files={"file": ("clean_me.pdf", VALID_PDF, "application/pdf")},
                headers=headers,
            )
        assert len(deleted_keys) == 1
        with pytest.raises(ObjectNotFoundError):
            await real_storage.get(deleted_keys[0])
    finally:
        set_storage_override(None)


async def test_s3_storage_backend_sigv4_put_get_delete():
    objects: dict[str, bytes] = {}
    seen_headers: list[dict[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.append(dict(request.headers))
        path = request.url.path
        if request.method == "PUT":
            objects[path] = request.content
            return httpx.Response(200)
        if request.method == "GET":
            if path not in objects:
                return httpx.Response(404)
            return httpx.Response(200, content=objects[path])
        if request.method == "DELETE":
            objects.pop(path, None)
            return httpx.Response(204)
        return httpx.Response(405)

    s3 = S3StorageBackend(
        bucket="rtn-vault-prod",
        region="ap-south-1",
        access_key_id="AKIAIOSFODNN7EXAMPLE",
        secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        endpoint_url="https://s3.ap-south-1.amazonaws.com",
        transport=httpx.MockTransport(handler),
    )

    key = "vault/u123/d456.pdf"
    await s3.put(key, VALID_PDF, "application/pdf")
    assert seen_headers[-1]["authorization"].startswith("AWS4-HMAC-SHA256 Credential=AKIAIOSFODNN7EXAMPLE/")
    assert seen_headers[-1]["x-amz-content-sha256"] == hashlib.sha256(VALID_PDF).hexdigest()

    fetched = await s3.get(key)
    assert fetched == VALID_PDF

    await s3.delete(key)
    with pytest.raises(ObjectNotFoundError):
        await s3.get(key)


async def test_external_malware_scanner_integration(client):
    headers, _ = await _register_user(client, "scan@example.com")

    # 1. Infected file is rejected with 422 and never stored
    infected_scanner = ExternalHttpMalwareScanner(
        "http://scanner.internal/scan",
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json={"clean": False, "detail": "Eicar-Test-Signature"})),
    )
    set_scanner_override(infected_scanner)
    try:
        r_inf = await client.post(
            "/documents",
            files={"file": ("infected.pdf", VALID_PDF, "application/pdf")},
            headers=headers,
        )
        assert r_inf.status_code == 422
        assert r_inf.json()["detail"]["code"] == "malware_detected"
        assert (await client.get("/documents", headers=headers)).json()["total"] == 0

        # 2. Clean file scanned by external scanner is marked scan_status="clean"
        clean_scanner = ExternalHttpMalwareScanner(
            "http://scanner.internal/scan",
            transport=httpx.MockTransport(lambda req: httpx.Response(200, json={"clean": True})),
        )
        set_scanner_override(clean_scanner)
        r_clean = await client.post(
            "/documents",
            files={"file": ("verified.pdf", VALID_PDF, "application/pdf")},
            headers=headers,
        )
        assert r_clean.status_code == 201
        assert r_clean.json()["scan_status"] == "clean"

        # 3. Unreachable external scanner fails closed with 503
        down_scanner = ExternalHttpMalwareScanner(
            "http://scanner.internal/scan",
            transport=httpx.MockTransport(lambda req: httpx.Response(503)),
        )
        set_scanner_override(down_scanner)
        r_down = await client.post(
            "/documents",
            files={"file": ("blocked.pdf", VALID_PDF, "application/pdf")},
            headers=headers,
        )
        assert r_down.status_code == 503
        assert r_down.json()["detail"]["code"] == "scanner_unavailable"
    finally:
        set_scanner_override(None)


async def test_document_deletion_session_deletion_and_account_erasure(client):
    headers, _ = await _register_user(client, "priv@example.com")
    assert (await client.post("/consent", json={"purpose": "service", "granted": True}, headers=headers)).status_code == 201
    sid = (await client.post("/sessions", json={"goal": "I want to open a small bakery in Kolkata", "language": "en"}, headers=headers)).json()["id"]

    # Upload 3 documents: doc1 (to delete manually), doc2 (tied to session), doc3 (general account doc)
    d1 = (await client.post("/documents", files={"file": ("one.pdf", VALID_PDF, "application/pdf")}, headers=headers)).json()
    d2 = (await client.post("/documents", data={"session_id": sid}, files={"file": ("two.png", VALID_PNG, "image/png")}, headers=headers)).json()
    d3 = (await client.post("/documents", files={"file": ("three.jpg", VALID_JPEG, "image/jpeg")}, headers=headers)).json()

    async with maker()() as db:
        keys = {
            d.id: d.stored_object_key
            for d in (await db.execute(select(Document).where(Document.id.in_([d1["id"], d2["id"], d3["id"]])))).scalars()
        }

    # Privacy export includes all 3 active documents
    exp = (await client.get("/privacy/export", headers=headers)).json()
    assert {d["id"] for d in exp["documents"]} == {d1["id"], d2["id"], d3["id"]}

    # Delete doc1 -> storage object is removed and subsequent download/get returns 404
    del_r = await client.delete(f"/documents/{d1['id']}", headers=headers)
    assert del_r.status_code == 200 and del_r.json()["deleted"] is True
    assert (await client.get(f"/documents/{d1['id']}", headers=headers)).status_code == 404
    assert (await client.get(f"/documents/{d1['id']}/download", headers=headers)).status_code == 404
    with pytest.raises(ObjectNotFoundError):
        await get_storage().get(keys[d1["id"]])

    # Delete session -> removes private session-linked doc2 from storage and DB, keeps doc3
    assert (await client.delete(f"/privacy/sessions/{sid}", headers=headers)).status_code == 204
    with pytest.raises(ObjectNotFoundError):
        await get_storage().get(keys[d2["id"]])
    remaining = (await client.get("/documents", headers=headers)).json()["items"]
    assert [d["id"] for d in remaining] == [d3["id"]]

    # Delete account -> removes doc3 from storage and DB, and revokes access
    assert (await client.delete("/privacy/me", headers=headers)).status_code == 200
    with pytest.raises(ObjectNotFoundError):
        await get_storage().get(keys[d3["id"]])
    async with maker()() as db:
        assert (await db.execute(select(Document))).scalars().all() == []
    assert (await client.get("/documents", headers=headers)).status_code == 401
