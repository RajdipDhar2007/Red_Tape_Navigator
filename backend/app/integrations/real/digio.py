"""Digio adapters: Aadhaar eSign (Digi Sign) and DigiLocker (DigiStudio KYC workflow).

Every endpoint and field below was read from documentation.digio.in (see docs/INTEGRATIONS.md, "Digio facts").
Anything the docs did not show is deliberately NOT guessed: in particular the exact data fields of a completed
DigiLocker result are not mapped yet, so ``fields`` is always empty until verified against the sandbox.

Auth is HTTP Basic (client id : client secret). Sandbox base ``https://ext.digio.in:444``, production
``https://api.digio.in``. Neither the secret nor personal data (identifiers, names, PDFs) is ever logged.
"""
import json
import logging

import httpx

from app.integrations.interfaces import (
    STATUS_COMPLETED,
    STATUS_EXPIRED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_REJECTED,
    AdapterResult,
)

log = logging.getLogger(__name__)

BASE_URLS = {"sandbox": "https://ext.digio.in:444", "production": "https://api.digio.in"}

# Digi Sign document agreement_status -> our status (docs: draft|requested|completed|expired|failed)
_DOC_STATUS = {"draft": STATUS_PENDING, "requested": STATUS_PENDING, "completed": STATUS_COMPLETED,
               "expired": STATUS_EXPIRED, "failed": STATUS_FAILED}
# DigiStudio request status (docs: requested|approval_pending|approved|rejected|failed|expired|skipped)
_KYC_STATUS = {"requested": STATUS_PENDING, "approval_pending": STATUS_PENDING, "approved": STATUS_COMPLETED,
               "rejected": STATUS_REJECTED, "failed": STATUS_FAILED, "expired": STATUS_EXPIRED, "skipped": STATUS_FAILED}

# Digi Sign error codes (docs "Error Codes") -> message that is safe and useful to show a citizen.
FRIENDLY_ERRORS = {
    "1015": "Signing is temporarily unavailable. Please try again later.",       # provider credits exhausted: operator issue
    "1073": "Signing is temporarily unavailable. Please try again later.",
    "1079": "The signer details are not valid. Check your email or mobile number.",
    "1050": "The email address is not valid.",
    "1108": "This signing request has expired. Start a new one.",
    "1155": "This signing request has expired. Start a new one.",
    "998": "Too many attempts. Start a new signing request.",
    "1055": "You have already signed this document.",
    "1081": "The document could not be read as a PDF.",
    "1037": "The document is too large to sign.",
    "1128": "A duplicate request was received. Wait a few minutes and retry.",
    "1205": "Aadhaar signing is temporarily unavailable at UIDAI. Try again later.",
    "1001": "Digio had a system error. Try again later.",
    "1199": "Digio is temporarily unavailable. Try again later.",
}


def normalise_doc_status(value: str | None) -> str:
    return _DOC_STATUS.get((value or "").lower(), STATUS_PENDING)


def normalise_kyc_status(value: str | None) -> str:
    return _KYC_STATUS.get((value or "").lower(), STATUS_PENDING)


class DigioClient:
    def __init__(self, client_id: str, client_secret: str, env: str = "sandbox", base_url: str = "",
                 transport: httpx.AsyncBaseTransport | None = None):
        self.base = (base_url or BASE_URLS.get(env, BASE_URLS["sandbox"])).rstrip("/")
        self._auth = (client_id, client_secret)
        self._transport = transport

    async def call(self, method: str, path: str, *, timeout: float = 30, retry: bool = False, **kw) -> tuple[httpx.Response | None, dict]:
        """Returns (response, parsed json or {}). Never raises for network/HTTP errors; response is None if unreachable.
        ``retry`` allows ONE more attempt after a network error or a 5xx reply; use it only for read-only calls."""
        r: httpx.Response | None = None
        for attempt in range(2 if retry else 1):
            try:
                async with httpx.AsyncClient(timeout=timeout, auth=self._auth, transport=self._transport) as c:
                    r = await c.request(method, self.base + path, **kw)
            except httpx.HTTPError as exc:
                log.warning("digio unreachable: %s %s (attempt %d)", type(exc).__name__, path.split("?")[0], attempt + 1)
                r = None
                continue
            if r.status_code < 500:
                break
        if r is None:
            return None, {}
        data: dict = {}
        if r.headers.get("content-type", "").startswith("application/json"):
            try:
                parsed = r.json()
                data = parsed if isinstance(parsed, dict) else {}
            except ValueError:
                data = {}
        return r, data


def _failure(r: httpx.Response | None, data: dict, what: str) -> AdapterResult:
    if r is None:
        return AdapterResult(False, {"error": "provider_unreachable"}, False, "Signing provider unreachable. Try again later.")
    code = str(data.get("code") or data.get("error_code") or "")
    log.warning("digio %s failed: status=%s code=%s", what, r.status_code, code)  # no identifiers, no bodies
    label = FRIENDLY_ERRORS.get(code, "The provider could not complete the request. Try again later.")
    return AdapterResult(False, {"error": "provider_rejected", "http_status": r.status_code, "code": code}, False, label)


class DigioESign:
    mock = False

    def __init__(self, client: DigioClient, expire_in_days: int = 7):
        self.c, self.expire_in_days = client, expire_in_days

    async def create_request(self, pdf: bytes, file_name: str, signer_identifier: str, reason: str, reference_id: str) -> AdapterResult:
        request = {
            "file_name": file_name,
            "signers": [{"identifier": signer_identifier, "reason": reason[:250], "sign_type": "aadhaar"}],
            "expire_in_days": self.expire_in_days,
            "display_on_page": "last",
            "notify_signers": True,
            "will_self_sign": False,
            "callback": reference_id,  # Digio uses this for idempotency: the same value returns the earlier document
            "include_authentication_url": True,
        }
        files = {"file": (file_name, pdf, "application/pdf"), "request": (None, json.dumps(request), "text/plain")}
        r, data = await self.c.call("POST", "/v2/client/document/upload", files=files, timeout=60)
        if r is None or r.status_code != 200 or not data.get("id"):
            return _failure(r, data, "esign.create")
        parties = data.get("signing_parties") or []
        url = next((p.get("authentication_url") for p in parties if isinstance(p, dict) and p.get("authentication_url")), None)
        return AdapterResult(True, {"document_id": data["id"], "status": normalise_doc_status(data.get("agreement_status")),
                                    "signing_url": url, "legally_valid": False}, False, None)

    async def get_status(self, document_id: str) -> AdapterResult:
        r, data = await self.c.call("GET", f"/v2/client/document/{document_id}", retry=True)
        if r is None or r.status_code != 200:
            return _failure(r, data, "esign.status")
        parties = [p for p in (data.get("signing_parties") or []) if isinstance(p, dict)]
        status = normalise_doc_status(data.get("agreement_status"))
        if status == STATUS_PENDING and parties and all(p.get("status") in ("failed", "cancelled", "removed") for p in parties):
            status = STATUS_FAILED
        return AdapterResult(True, {"document_id": document_id, "status": status}, False, None)

    async def download_signed(self, document_id: str) -> AdapterResult:
        r, data = await self.c.call("GET", f"/v2/client/document/download?document_id={document_id}", timeout=60, retry=True)
        if r is None or r.status_code != 200 or not r.content.startswith(b"%PDF"):
            return _failure(r, data, "esign.download")
        return AdapterResult(True, {"pdf": r.content}, False, None)


class DigioDigiLocker:
    mock = False

    def __init__(self, client: DigioClient, template_name: str = "DIGILOCKER_AADHAAR_PAN", expire_in_days: int = 2):
        self.c, self.template, self.expire_in_days = client, template_name, expire_in_days

    async def start_request(self, customer_identifier: str, customer_name: str, reference_id: str) -> AdapterResult:
        body = {"customer_identifier": customer_identifier, "customer_name": customer_name or None, "template_name": self.template,
                "reference_id": reference_id, "transaction_id": reference_id, "notify_customer": True,
                "expire_in_days": self.expire_in_days, "generate_access_token": False}
        r, data = await self.c.call("POST", "/client/kyc/v2/request/with_template", json={k: v for k, v in body.items() if v is not None})
        if r is None or r.status_code != 200 or not data.get("id"):
            return _failure(r, data, "digilocker.start")
        # notify_customer makes Digio send the citizen the consent link by email/SMS; the result arrives by webhook/status.
        return AdapterResult(True, {"request_id": data["id"], "status": normalise_kyc_status(data.get("status")), "fields": {}}, False, None)

    async def get_status(self, request_id: str) -> AdapterResult:
        r, data = await self.c.call("POST", f"/client/kyc/v2/{request_id}/response", retry=True)
        if r is None or r.status_code != 200:
            return _failure(r, data, "digilocker.status")
        # Field mapping of the returned Aadhaar/PAN data is NOT implemented until verified in the sandbox.
        return AdapterResult(True, {"request_id": request_id, "status": normalise_kyc_status(data.get("status")), "fields": {}}, False, None)
