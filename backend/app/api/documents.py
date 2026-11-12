"""Secure Document Vault API for user-owned supporting documents.

- Never trusts client-provided user IDs.
- Enforces strict MIME, extension, and magic-byte allowlists (PDF, PNG, JPEG).
- Enforces configurable max upload size and rejects empty files.
- Generates opaque server-side storage keys (never uses raw filenames).
- Cleans up storage objects if DB persistence fails or when documents/accounts are deleted.
"""
import hashlib
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.core import audit
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.scanner import ScannerUnavailableError, get_scanner
from app.core.storage import ObjectNotFoundError, StorageError, get_storage
from app.db.models import Document, NavSession, User, WorkspaceMember
from app.db.session import get_db

router = APIRouter(prefix="/documents", tags=["documents"])
_log = get_logger("documents")

ALLOWED_TYPES: dict[str, tuple[set[str], str, bytes]] = {
    "application/pdf": ({".pdf"}, "pdf", b"%PDF-"),
    "image/png": ({".png"}, "png", b"\x89PNG\r\n\x1a\n"),
    "image/jpeg": ({".jpg", ".jpeg"}, "jpg", b"\xff\xd8\xff"),
}
CONTENT_TYPE_ALIASES: dict[str, str] = {
    "image/jpg": "image/jpeg",
}
FORBIDDEN_EXTENSIONS = {
    "exe", "dll", "bat", "cmd", "sh", "bash", "ps1", "vbs", "js", "mjs", "cjs",
    "html", "htm", "xhtml", "svg", "xml", "php", "py", "rb", "pl", "jar", "msi", "scr", "com",
}
ALLOWED_CATEGORIES = {"general", "identity", "premises", "business", "licence"}
CHUNK_SIZE = 65_536


def _sanitize_filename(raw_filename: str | None, canonical_ext: str) -> tuple[str, str]:
    """Return (safe_display_filename, lowercase_extension_with_dot) without path traversal or control chars."""
    raw = (raw_filename or "").strip()
    base = re.split(r"[/\\]", raw)[-1]
    base = re.sub(r"[\x00-\x1f\x7f\"'<>|:*?]", "", base).strip()
    while ".." in base:
        base = base.replace("..", ".")
    base = base.lstrip(".")
    if not base:
        base = f"document.{canonical_ext}"
    ext = Path(base).suffix.lower()
    stem = Path(base).stem if ext else base
    stem = re.sub(r"[^A-Za-z0-9._ -]", "_", stem).strip(" ._") or "document"
    stem = stem[:180]
    final_ext = ext if ext else f".{canonical_ext}"
    return f"{stem}{final_ext}", ext


def _validate_type_and_name(content_type: str | None, raw_filename: str | None) -> tuple[str, str, bytes, str]:
    raw_ct = (content_type or "").split(";")[0].strip().lower()
    norm_ct = CONTENT_TYPE_ALIASES.get(raw_ct, raw_ct)
    if norm_ct not in ALLOWED_TYPES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            {"code": "unsupported_file_type", "message": "Only PDF, PNG, and JPEG documents are allowed."},
        )
    allowed_exts, canonical_ext, magic = ALLOWED_TYPES[norm_ct]
    safe_name, ext = _sanitize_filename(raw_filename, canonical_ext)

    # Reject any dangerous executable or script extension anywhere in the filename parts
    raw_base = re.split(r"[/\\]", (raw_filename or "").strip())[-1].lower()
    parts = [p.strip() for p in raw_base.split(".")[1:] if p.strip()]
    if any(p in FORBIDDEN_EXTENSIONS for p in parts):
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            {"code": "unsupported_file_type", "message": "Executable or script file extensions are not allowed."},
        )
    if ext and ext not in allowed_exts:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            {"code": "extension_mismatch", "message": "File extension does not match the declared document type."},
        )
    return norm_ct, canonical_ext, magic, safe_name


def _serialize_doc(doc: Document, viewer_id: str) -> dict:
    return {
        "id": doc.id,
        "original_filename": doc.original_filename,
        "content_type": doc.content_type,
        "size_bytes": doc.size_bytes,
        "checksum": doc.checksum,
        "category": doc.category,
        "workspace_id": doc.workspace_id,
        "session_id": doc.session_id,
        "scan_status": doc.scan_status,
        "is_owner": doc.user_id == viewer_id,
        "created_at": doc.created_at.isoformat(),
        "updated_at": doc.updated_at.isoformat(),
    }


async def _get_accessible_doc(db: AsyncSession, user: User, doc_id: str) -> Document:
    doc = await db.get(Document, doc_id)
    if doc is None or doc.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    if doc.user_id == user.id:
        return doc
    if doc.workspace_id:
        member = await db.get(WorkspaceMember, (doc.workspace_id, user.id))
        if member is not None:
            return doc
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form(default="general"),
    workspace_id: str | None = Form(default=None),
    session_id: str | None = Form(default=None),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    cat = (category or "general").strip().lower()
    if cat not in ALLOWED_CATEGORIES:
        raise HTTPException(422, "Invalid document category")

    norm_ct, canonical_ext, magic, safe_name = _validate_type_and_name(file.content_type, file.filename)

    wid = workspace_id.strip() if workspace_id and workspace_id.strip() else None
    if wid is not None:
        if await db.get(WorkspaceMember, (wid, user.id)) is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")

    sid = session_id.strip() if session_id and session_id.strip() else None
    if sid is not None:
        ns = await db.get(NavSession, sid)
        if ns is None or ns.user_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")

    s = get_settings()
    max_bytes = s.max_upload_bytes
    hasher = hashlib.sha256()
    chunks: list[bytes] = []
    total_bytes = 0

    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        total_bytes += len(chunk)
        if total_bytes > max_bytes:
            raise HTTPException(
                413,
                {
                    "code": "file_too_large",
                    "message": f"File exceeds the maximum allowed size of {max(1, max_bytes // (1024 * 1024))} MB.",
                },
            )
        hasher.update(chunk)
        chunks.append(chunk)

    if total_bytes == 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            {"code": "empty_file", "message": "Uploaded file is empty."},
        )

    data = b"".join(chunks)
    if not data.startswith(magic):
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            {"code": "invalid_file_signature", "message": "File content does not match the declared file type."},
        )

    checksum = hasher.hexdigest()

    try:
        scan_res = await get_scanner().scan(data, safe_name, norm_ct, checksum)
    except ScannerUnavailableError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            {"code": "scanner_unavailable", "message": str(exc)},
        ) from exc

    if not scan_res.clean:
        await audit.record(
            db,
            user.id,
            "document.rejected_malware",
            {"content_type": norm_ct, "size_bytes": total_bytes, "checksum": checksum},
            sid,
        )
        raise HTTPException(
            422,
            {"code": "malware_detected", "message": "Upload rejected by security scan."},
        )

    scan_status = "clean" if scan_res.mode == "external" else "disabled"
    doc_id = uuid.uuid4().hex
    object_key = f"vault/{user.id}/{doc_id}.{canonical_ext}"

    storage = get_storage()
    try:
        await storage.put(object_key, data, norm_ct)
    except StorageError as exc:
        _log.warning("document_storage_put_failed", user_id=user.id, error_type=type(exc).__name__)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            {"code": "storage_unavailable", "message": "Could not store document. Please try again."},
        ) from exc

    doc = Document(
        id=doc_id,
        user_id=user.id,
        workspace_id=wid,
        session_id=sid,
        original_filename=safe_name,
        stored_object_key=object_key,
        content_type=norm_ct,
        size_bytes=total_bytes,
        checksum=checksum,
        category=cat,
        scan_status=scan_status,
    )
    try:
        db.add(doc)
        await db.commit()
    except Exception:
        await db.rollback()
        try:
            await storage.delete(object_key)
        except Exception as cleanup_exc:  # noqa: BLE001
            _log.warning("document_orphan_cleanup_failed", doc_id=doc_id, error_type=type(cleanup_exc).__name__)
        raise

    await audit.record(
        db,
        user.id,
        "document.uploaded",
        {
            "document_id": doc.id,
            "content_type": doc.content_type,
            "size_bytes": doc.size_bytes,
            "checksum": doc.checksum,
            "category": doc.category,
            "scan_status": doc.scan_status,
        },
        sid,
    )
    return _serialize_doc(doc, user.id)


@router.get("")
async def list_documents(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    workspace_id: str | None = Query(default=None),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    wid = workspace_id.strip() if workspace_id and workspace_id.strip() else None
    if wid is not None:
        if await db.get(WorkspaceMember, (wid, user.id)) is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")
        cond = (Document.workspace_id == wid) & Document.deleted_at.is_(None)
    else:
        cond = (Document.user_id == user.id) & Document.deleted_at.is_(None)

    total = (await db.execute(select(func.count()).select_from(Document).where(cond))).scalar_one()
    rows = (
        await db.execute(
            select(Document).where(cond).order_by(Document.created_at.desc(), Document.id.desc()).offset(offset).limit(limit)
        )
    ).scalars().all()
    s = get_settings()
    return {
        "items": [_serialize_doc(d, user.id) for d in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
        "max_upload_bytes": s.max_upload_bytes,
        "allowed_types": sorted(ALLOWED_TYPES.keys()),
        "scan_mode": s.document_scan_mode,
    }


@router.get("/{doc_id}")
async def get_document_metadata(
    doc_id: str,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await _get_accessible_doc(db, user, doc_id)
    return _serialize_doc(doc, user.id)


@router.get("/{doc_id}/download")
async def download_document(
    doc_id: str,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await _get_accessible_doc(db, user, doc_id)
    try:
        data = await get_storage().get(doc.stored_object_key)
    except ObjectNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document file not found") from exc
    except StorageError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Document storage temporarily unavailable") from exc

    await audit.record(db, user.id, "document.downloaded", {"document_id": doc.id}, doc.session_id)
    ascii_name = re.sub(r"[^A-Za-z0-9._-]", "_", doc.original_filename) or f"document-{doc.id[:8]}"
    return Response(
        content=data,
        media_type=doc.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{ascii_name}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await db.get(Document, doc_id)
    if doc is None or doc.deleted_at is not None or doc.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")

    try:
        await get_storage().delete(doc.stored_object_key)
    except StorageError as exc:
        _log.warning("document_storage_delete_failed", doc_id=doc.id, error_type=type(exc).__name__)

    doc.deleted_at = datetime.now(UTC)
    doc.workspace_id = None
    doc.session_id = None
    await db.commit()
    await audit.record(db, user.id, "document.deleted", {"document_id": doc.id})
    return {"deleted": True, "id": doc.id}
