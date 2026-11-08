"""Real WhatsApp Business / SMS / Email adapters - STUBS.

Required to go live: WhatsApp Business Platform account + approved message templates (Meta/BSP), DLT registration
and approved templates for SMS (TRAI), SMTP/SES credentials with verified sender domain for email.
See docs/INTEGRATIONS.md.
"""
from app.integrations.interfaces import AdapterResult


class RealMessenger:
    def __init__(self, channel: str, **credentials: str):
        self.channel = channel
        self.credentials = credentials

    async def send(self, to: str, text: str, subject: str = "Red Tape Navigator") -> AdapterResult:
        raise NotImplementedError(f"{self.channel} adapter requires provider onboarding; see docs/INTEGRATIONS.md")
