"""Pluggable malware-scanning interface for user document uploads.

Never claims a file was scanned when DOCUMENT_SCAN_MODE=disabled.
"""
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

_log = get_logger("scanner")


class ScannerUnavailableError(Exception):
    """Raised when DOCUMENT_SCAN_MODE=external and the scanner cannot be reached."""


@dataclass(frozen=True)
class ScanResult:
    clean: bool
    mode: str  # "disabled" | "external"
    detail: str | None = None


class MalwareScanner(Protocol):
    async def scan(self, data: bytes, filename: str, content_type: str, sha256: str) -> ScanResult: ...


class DisabledMalwareScanner:
    """Development/non-scanned mode. Explicitly marks scan_status as 'disabled'."""

    async def scan(self, data: bytes, filename: str, content_type: str, sha256: str) -> ScanResult:
        return ScanResult(clean=True, mode="disabled", detail="malware_scanning_disabled")


class ExternalHttpMalwareScanner:
    """Calls an external HTTP malware scanning service (e.g., ClamAV REST bridge) before storing uploads."""

    def __init__(self, url: str, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.url = url
        self._transport = transport

    async def scan(self, data: bytes, filename: str, content_type: str, sha256: str) -> ScanResult:
        try:
            async with httpx.AsyncClient(timeout=15.0, transport=self._transport) as client:
                resp = await client.post(
                    self.url,
                    data={"sha256": sha256, "content_type": content_type},
                    files={"file": (filename, data, content_type)},
                )
        except httpx.HTTPError as exc:
            _log.warning("malware_scanner_unreachable", error_type=type(exc).__name__)
            raise ScannerUnavailableError("Document malware scanner is temporarily unavailable") from exc
        if resp.status_code != 200:
            _log.warning("malware_scanner_bad_status", status=resp.status_code)
            raise ScannerUnavailableError("Document malware scanner returned an unexpected status")
        body = resp.json()
        clean = bool(body.get("clean", False))
        detail = str(body.get("detail") or ("clean" if clean else "threat_detected"))
        return ScanResult(clean=clean, mode="external", detail=detail)


_scanner_override: MalwareScanner | None = None


def set_scanner_override(scanner: MalwareScanner | None) -> None:
    global _scanner_override
    _scanner_override = scanner


def get_scanner() -> MalwareScanner:
    if _scanner_override is not None:
        return _scanner_override
    s = get_settings()
    if s.document_scan_mode == "external":
        if not s.document_scan_url:
            raise ScannerUnavailableError("DOCUMENT_SCAN_URL is not configured for external scan mode")
        return ExternalHttpMalwareScanner(s.document_scan_url)
    return DisabledMalwareScanner()

