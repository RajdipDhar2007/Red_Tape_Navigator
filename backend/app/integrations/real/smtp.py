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


class SmtpEmail:
    channel = "email"

    def __init__(self, host: str, port: int, username: str, password: str, sender: str, starttls: bool = True):
        self.host, self.port, self.username, self.password = host, port, username, password
        self.sender, self.starttls = sender, starttls

    def _send_sync(self, to: str, subject: str, text: str) -> None:
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = self.sender, to, subject
        msg.set_content(text)
        ctx = ssl.create_default_context()
        if self.port == 465:
            with smtplib.SMTP_SSL(self.host, self.port, timeout=20, context=ctx) as s:
                self._deliver(s, msg)
        else:
            with smtplib.SMTP(self.host, self.port, timeout=20) as s:
                if self.starttls:
                    s.starttls(context=ctx)
                self._deliver(s, msg)

    def _deliver(self, s: smtplib.SMTP, msg: EmailMessage) -> None:
        if self.username:
            s.login(self.username, self.password)
        s.send_message(msg)

    async def send(self, to: str, text: str, subject: str = "Red Tape Navigator") -> AdapterResult:
        if "\n" in to or "\r" in to or "\n" in subject or "\r" in subject:  # header-injection guard
            return AdapterResult(False, {"error": "invalid header"})
        try:
            await asyncio.to_thread(self._send_sync, to, subject, text)
        except (OSError, smtplib.SMTPException):
            log.exception("email delivery failed")  # never log the recipient or body
            return AdapterResult(False, {"error": "delivery failed"})
        return AdapterResult(True, {"sent": True})
