"""Real email delivery over SMTP (STARTTLS or implicit TLS). Works with any provider: SES, SendGrid, Gmail, NIC mail.

Needs SMTP_HOST (+ SMTP_USERNAME / SMTP_PASSWORD / SMTP_FROM). Use a verified sender domain (SPF/DKIM) so citizen
mail is not marked as spam. Blocking smtplib runs in a worker thread so the event loop is never blocked.
"""
import asyncio
import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.integrations.interfaces import AdapterResult

log = logging.getLogger(__name__)


def _is_transient_smtp_error(exc: BaseException) -> bool:
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return False
    if isinstance(exc, (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError)):
        return True
    if isinstance(exc, smtplib.SMTPResponseException):
        return 400 <= exc.smtp_code < 500
    return isinstance(exc, (TimeoutError, OSError))


class SmtpEmail:
    channel = "email"
    mock = False

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        sender: str,
        starttls: bool = True,
        *,
        timeout: float = 20.0,
        retries: int = 1,
    ):
        self.host, self.port, self.username, self.password = host.strip(), port, username, password
        self.sender, self.starttls = sender.strip(), starttls
        self.timeout = timeout
        self.retries = max(0, retries)

    def _send_sync(self, to: str, subject: str, text: str) -> None:
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = self.sender, to, subject
        msg.set_content(text)
        ctx = ssl.create_default_context()
        if self.port == 465:
            with smtplib.SMTP_SSL(self.host, self.port, timeout=self.timeout, context=ctx) as s:
                self._deliver(s, msg)
        else:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as s:
                if self.starttls:
                    s.starttls(context=ctx)
                self._deliver(s, msg)

    def _deliver(self, s: smtplib.SMTP, msg: EmailMessage) -> None:
        if self.username:
            s.login(self.username, self.password)
        refused = s.send_message(msg)
        if refused:
            raise smtplib.SMTPRecipientsRefused(refused)

    async def send(self, to: str, text: str, subject: str = "Red Tape Navigator") -> AdapterResult:
        if not (self.host and self.sender):
            return AdapterResult(
                False,
                {"error": "not_configured", "delivery_status": "not_configured"},
                False,
                "Email provider not configured",
            )
        if any(ch in val for val in (to, subject, self.sender) for ch in ("\n", "\r", "\x00")):
            return AdapterResult(False, {"error": "invalid header", "delivery_status": "rejected"}, False)
        last_exc: BaseException | None = None
        for attempt in range(self.retries + 1):
            try:
                await asyncio.wait_for(
                    asyncio.to_thread(self._send_sync, to, subject, text),
                    timeout=self.timeout + 5.0,
                )
                return AdapterResult(
                    True,
                    {
                        "sent": True,
                        "smtp_accepted": True,
                        "delivery_status": "smtp_accepted",
                        "recipient_delivery_confirmed": False,
                    },
                    False,
                    None,
                )
            except (OSError, smtplib.SMTPException, TimeoutError) as exc:
                last_exc = exc
                # Never log recipient address, message body, reset tokens, username, or password
                log.warning(
                    "email delivery failed: error_type=%s attempt=%d",
                    type(exc).__name__,
                    attempt + 1,
                )
                if attempt < self.retries and _is_transient_smtp_error(exc):
                    continue
                break
        err_kind = "timeout" if isinstance(last_exc, TimeoutError) else "delivery failed"
        return AdapterResult(
            False,
            {"error": err_kind, "delivery_status": "failed"},
            False,
            "Email could not be accepted by the SMTP server",
        )
