"""Payment providers. Hosted checkout only: card, UPI and bank details are typed on the provider's page, never here.

``MockProvider`` is the default (no network, no money). ``RazorpayProvider`` creates a hosted Payment Link and is meant for
Razorpay TEST keys until the owner decides otherwise. Its request/response shapes follow Razorpay's public API docs and have
NOT been exercised against a live account (docs/INTEGRATIONS.md).
"""
import hashlib
import hmac
import logging
from dataclasses import dataclass

import httpx

log = logging.getLogger(__name__)


@dataclass
class Checkout:
    ok: bool
    provider_ref: str | None = None
    url: str | None = None
    error: str | None = None


def verify_razorpay_signature(secret: str, body: bytes, header: str) -> bool:
    """Razorpay signs the raw webhook body with HMAC-SHA256 (hex) using the webhook secret; header ``X-Razorpay-Signature``."""
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, (header or "").strip())


class MockProvider:
    name = "mock"

    async def create_checkout(self, order_id: str, amount_paise: int, description: str, email: str, return_url: str) -> Checkout:
        # The page at this URL does not exist in production builds; the dev-only /billing/mock/pay endpoint settles the order.
        return Checkout(True, f"mock_{order_id}", f"{return_url}?mock_order={order_id}")


class RazorpayProvider:
    name = "razorpay"
    API = "https://api.razorpay.com/v1/payment_links"

    def __init__(self, key_id: str, key_secret: str, transport: httpx.AsyncBaseTransport | None = None):
        self._auth, self._transport = (key_id, key_secret), transport

    async def create_checkout(self, order_id: str, amount_paise: int, description: str, email: str, return_url: str) -> Checkout:
        body = {
            "amount": amount_paise, "currency": "INR", "reference_id": order_id, "description": description[:2000],
            "customer": {"email": email}, "notify": {"email": False, "sms": False},
            "callback_url": return_url, "callback_method": "get", "notes": {"order_id": order_id},
        }
        try:
            async with httpx.AsyncClient(timeout=20, auth=self._auth, transport=self._transport) as c:
                r = await c.post(self.API, json=body)
            data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("razorpay unreachable: %s", type(exc).__name__)
            return Checkout(False, error="Payment provider unreachable. Try again later.")
        if r.status_code not in (200, 201) or not data.get("short_url"):
            log.warning("razorpay rejected checkout: status=%s", r.status_code)  # never log the body
            return Checkout(False, error="The payment provider could not start the payment.")
        return Checkout(True, str(data.get("id")), str(data["short_url"]))


def get_provider(settings):
    if settings.billing_provider == "razorpay" and settings.razorpay_key_id and settings.razorpay_key_secret:
        return RazorpayProvider(settings.razorpay_key_id, settings.razorpay_key_secret)
    return MockProvider()
