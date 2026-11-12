"""Storage abstraction for user-owned Document Vault objects (local filesystem for dev/test, S3-compatible for prod)."""
import asyncio
import hashlib
import hmac
import os
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from urllib.parse import quote, urlsplit

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

_log = get_logger("storage")
_KEY_RE = re.compile(r"^[A-Za-z0-9._/-]+$")


class StorageError(Exception):
    """Base error for document storage operations."""


class ObjectNotFoundError(StorageError):
    """Raised when a requested storage object does not exist."""


def validate_object_key(key: str) -> str:
    if (
        not key
        or len(key) > 512
        or key.startswith(("/", "\\", "."))
        or ".." in key.split("/")
        or "\\" in key
        or "\x00" in key
        or not _KEY_RE.match(key)
    ):
        raise StorageError("Invalid storage object key")
    return key


class StorageBackend(Protocol):
    async def put(self, key: str, data: bytes, content_type: str) -> None: ...
    async def get(self, key: str) -> bytes: ...
    async def delete(self, key: str) -> None: ...


class LocalStorageBackend:
    """Safe local filesystem object store with path-traversal protection and atomic temp-file writes."""

    def __init__(self, base_dir: str | Path) -> None:
        self.root = Path(base_dir).resolve()

    def _safe_path(self, key: str) -> Path:
        clean = validate_object_key(key)
        target = (self.root / clean).resolve()
        if not target.is_relative_to(self.root) or target == self.root:
            raise StorageError("Storage path escapes root directory")
        return target

    def _put_sync(self, key: str, data: bytes) -> None:
        target = self._safe_path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.parent / f".part-{uuid.uuid4().hex}"
        try:
            with open(tmp, "wb") as fh:
                fh.write(data)
                fh.flush()
            os.replace(tmp, target)
        except Exception as exc:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            raise StorageError(f"Failed to store object ({type(exc).__name__})") from exc

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        await asyncio.to_thread(self._put_sync, key, data)

    def _get_sync(self, key: str) -> bytes:
        target = self._safe_path(key)
        if not target.is_file():
            raise ObjectNotFoundError("Document object not found")
        try:
            return target.read_bytes()
        except OSError as exc:
            raise StorageError(f"Failed to read object ({type(exc).__name__})") from exc

    async def get(self, key: str) -> bytes:
        return await asyncio.to_thread(self._get_sync, key)

    def _delete_sync(self, key: str) -> None:
        target = self._safe_path(key)
        try:
            target.unlink(missing_ok=True)
        except OSError as exc:
            raise StorageError(f"Failed to delete object ({type(exc).__name__})") from exc

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._delete_sync, key)


def _hmac_sha256(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _signing_key(secret: str, date_stamp: str, region: str, service: str = "s3") -> bytes:
    k_date = _hmac_sha256(("AWS4" + secret).encode("utf-8"), date_stamp)
    k_region = _hmac_sha256(k_date, region)
    k_service = _hmac_sha256(k_region, service)
    return _hmac_sha256(k_service, "aws4_request")


class S3StorageBackend:
    """S3-compatible object storage backend using AWS Signature Version 4 over async httpx."""

    def __init__(
        self,
        *,
        bucket: str,
        region: str,
        access_key_id: str,
        secret_access_key: str,
        endpoint_url: str = "",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not (bucket and region and access_key_id and secret_access_key):
            raise StorageError("S3StorageBackend requires bucket, region, access_key_id, and secret_access_key")
        self.bucket = bucket.strip("/")
        self.region = region.strip()
        self.access_key_id = access_key_id.strip()
        self.secret_access_key = secret_access_key.strip()
        base = endpoint_url.strip().rstrip("/") if endpoint_url.strip() else f"https://s3.{self.region}.amazonaws.com"
        self.endpoint_url = base
        self._transport = transport

    def _build_signed_request(
        self,
        method: str,
        key: str,
        payload: bytes = b"",
        content_type: str | None = None,
        now: datetime | None = None,
    ) -> tuple[str, dict[str, str]]:
        clean_key = validate_object_key(key)
        now = now or datetime.now(UTC)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")

        parsed = urlsplit(self.endpoint_url)
        host = parsed.netloc
        base_path = parsed.path.rstrip("/")
        escaped_key = "/".join(quote(part, safe="-_.~") for part in clean_key.split("/"))
        canonical_uri = f"{base_path}/{quote(self.bucket, safe='-_.~')}/{escaped_key}"
        url = f"{parsed.scheme}://{host}{canonical_uri}"

        payload_hash = hashlib.sha256(payload).hexdigest()
        headers: dict[str, str] = {
            "host": host,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
        }
        if content_type:
            headers["content-type"] = content_type

        sorted_header_keys = sorted(headers.keys())
        canonical_headers = "".join(f"{k}:{headers[k].strip()}\n" for k in sorted_header_keys)
        signed_headers = ";".join(sorted_header_keys)
        canonical_request = "\n".join([
            method.upper(),
            canonical_uri,
            "",
            canonical_headers,
            signed_headers,
            payload_hash,
        ])

        credential_scope = f"{date_stamp}/{self.region}/s3/aws4_request"
        string_to_sign = "\n".join([
            "AWS4-HMAC-SHA256",
            amz_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ])
        sig_key = _signing_key(self.secret_access_key, date_stamp, self.region, "s3")
        signature = hmac.new(sig_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
        headers["Authorization"] = (
            f"AWS4-HMAC-SHA256 Credential={self.access_key_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )
        return url, headers

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        url, headers = self._build_signed_request("PUT", key, data, content_type=content_type)
        try:
            async with httpx.AsyncClient(timeout=30.0, transport=self._transport) as client:
                resp = await client.put(url, content=data, headers=headers)
        except httpx.HTTPError as exc:
            _log.warning("s3_put_error", error_type=type(exc).__name__)
            raise StorageError("Object storage upload failed") from exc
        if resp.status_code not in (200, 201, 204):
            _log.warning("s3_put_bad_status", status=resp.status_code)
            raise StorageError(f"Object storage upload rejected with status {resp.status_code}")

    async def get(self, key: str) -> bytes:
        url, headers = self._build_signed_request("GET", key)
        try:
            async with httpx.AsyncClient(timeout=30.0, transport=self._transport) as client:
                resp = await client.get(url, headers=headers)
        except httpx.HTTPError as exc:
            _log.warning("s3_get_error", error_type=type(exc).__name__)
            raise StorageError("Object storage download failed") from exc
        if resp.status_code == 404:
            raise ObjectNotFoundError("Document object not found in storage")
        if resp.status_code != 200:
            _log.warning("s3_get_bad_status", status=resp.status_code)
            raise StorageError(f"Object storage download failed with status {resp.status_code}")
        return resp.content

    async def delete(self, key: str) -> None:
        url, headers = self._build_signed_request("DELETE", key)
        try:
            async with httpx.AsyncClient(timeout=15.0, transport=self._transport) as client:
                resp = await client.delete(url, headers=headers)
        except httpx.HTTPError as exc:
            _log.warning("s3_delete_error", error_type=type(exc).__name__)
            raise StorageError("Object storage delete failed") from exc
        if resp.status_code not in (200, 202, 204, 404):
            _log.warning("s3_delete_bad_status", status=resp.status_code)
            raise StorageError(f"Object storage delete failed with status {resp.status_code}")


_storage_override: StorageBackend | None = None


def set_storage_override(backend: StorageBackend | None) -> None:
    global _storage_override
    _storage_override = backend


def get_storage() -> StorageBackend:
    if _storage_override is not None:
        return _storage_override
    s = get_settings()
    if s.storage_backend == "s3":
        return S3StorageBackend(
            bucket=s.storage_bucket,
            region=s.storage_region,
            access_key_id=s.storage_access_key_id,
            secret_access_key=s.storage_secret_access_key,
            endpoint_url=s.storage_endpoint_url,
        )
    return LocalStorageBackend(s.storage_local_dir)

