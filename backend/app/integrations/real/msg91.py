"""Real SMS delivery through MSG91's Flow API.

Indian SMS must use a TRAI DLT-registered template, so free text cannot be sent. Create a DLT template in the MSG91
dashboard that contains ONE variable (for example ``Red Tape Navigator reminder: ##var1##``), link it to a MSG91 flow
and set MSG91_TEMPLATE_ID to that flow's id. The reminder text is passed in that variable (MSG91_TEXT_VAR, default
``var1``). Keep the text short; the DLT template's own length rules apply.

Checked against docs.msg91.com/sms/send-sms (page updated 29 Oct 2026): POST /api/v5/flow, headers accept, authkey and
content-type, body template_id, short_url, recipients[].mobiles plus one key per template variable; a 200 returns
{"type": "success", "message": "<request id>"}. The docs' example names the variable VAR1; the key must match the variable
name in YOUR template exactly (case included), so set MSG91_TEXT_VAR to it. Still unverified against a live account.

Needs MSG91_AUTHKEY and MSG91_TEMPLATE_ID. Verify the request shape against your MSG91 account in sandbox/test mode
before go-live (docs/INTEGRATIONS.md); the provider rejects unapproved templates with DLT errors 203/211.
"""
import logging
import re

import httpx

from app.integrations.interfaces import AdapterResult

log = logging.getLogger(__name__)

FLOW_URL = "https://control.msg91.com/api/v5/flow"


def to_msisdn(number: str) -> str | None:
    """Indian mobile -> 91XXXXXXXXXX. Returns None when it is not a valid Indian mobile number."""
    digits = re.sub(r"\D", "", number or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return "91" + digits if re.fullmatch(r"[6-9]\d{9}", digits) else None


class Msg91Sms:
    channel = "sms"
    mock = False

    def __init__(
        self,
        authkey: str,
        template_id: str,
        text_var: str = "var1",
        url: str = FLOW_URL,
        *,
        timeout: float = 15.0,
    ):
        self.authkey = (authkey or "").strip()
        self.template_id = (template_id or "").strip()
        self.text_var = (text_var or "var1").strip() or "var1"
        self.url = url
        self.timeout = timeout

    async def send(self, to: str, text: str, subject: str = "Red Tape Navigator") -> AdapterResult:
        if not (self.authkey and self.template_id):
            return AdapterResult(False, {"error": "not_configured"}, False, "SMS provider not configured")
        msisdn = to_msisdn(to)
        if not msisdn:
            return AdapterResult(False, {"error": "invalid_mobile_number"}, False, "SMS not sent: invalid mobile number")
        body = {
            "template_id": self.template_id,
            "short_url": "0",
            "recipients": [{"mobiles": msisdn, self.text_var: text[:160]}],
        }
        r: httpx.Response | None = None
        data: dict = {}
        last_exc: BaseException | None = None
        for attempt in range(2):  # one retry, only for network errors and 5xx/429; the provider may rate-limit
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as c:
                    r = await c.post(self.url, json=body, headers={"authkey": self.authkey, "accept": "application/json"})
                data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            except (httpx.HTTPError, ValueError) as exc:
                last_exc = exc
                log.warning("msg91 request failed: %s (attempt %d)", type(exc).__name__, attempt + 1)
                r = None
                continue
            if r.status_code >= 500 or r.status_code == 429:
                continue
            break
        if r is None:
            err_data: dict[str, str] = {"error": "provider_unreachable"}
            if isinstance(last_exc, httpx.TimeoutException):
                err_data["reason"] = "timeout"
            return AdapterResult(False, err_data, False, "SMS provider unreachable")
        if not isinstance(data, dict):
            data = {}
        ok = r.status_code == 200 and str(data.get("type", "")).lower() == "success"
        if not ok:  # never log the phone number or message text
            log.warning("msg91 rejected request: status=%s type=%s", r.status_code, data.get("type"))
        info = {"status": r.status_code, "provider_type": data.get("type"), "message_id": data.get("message")}
        if not ok and data.get("code") is not None:
            info["provider_code"] = str(data.get("code"))  # e.g. DLT template errors 203/211, for the operator's log
        return AdapterResult(ok, info, False, None if ok else "SMS provider rejected the message")
