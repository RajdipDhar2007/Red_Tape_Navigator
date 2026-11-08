"""Integration interfaces (adapter pattern).

Deliberately NO method here submits anything to a government portal. e-Sign signs a document the citizen has
reviewed; DigiLocker only reads documents the citizen authorises; messaging only notifies.
"""
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class AdapterResult:
    ok: bool
    data: dict = field(default_factory=dict)
    mock: bool = False
    label: str | None = None  # shown in the UI, e.g. "Demo mode: simulated e-Sign"


# Normalised request states shared by every adapter. Provider-specific states are mapped onto these.
STATUS_PENDING = "pending"      # created, waiting for the citizen
STATUS_COMPLETED = "completed"  # signed / documents shared
STATUS_FAILED = "failed"        # provider or authentication error
STATUS_REJECTED = "rejected"    # citizen or provider rejected
STATUS_EXPIRED = "expired"
TERMINAL_STATUSES = {STATUS_COMPLETED, STATUS_FAILED, STATUS_REJECTED, STATUS_EXPIRED}


class DigiLocker(Protocol):
    """Consent-based document pull. The citizen approves inside the provider's flow; we only ever see the outcome."""

    mock: bool

    async def start_request(self, customer_identifier: str, customer_name: str, reference_id: str) -> AdapterResult:
        """data: request_id, status. Fields we are allowed to import (if any) come back under data['fields']."""
        ...

    async def get_status(self, request_id: str) -> AdapterResult:
        """data: status (normalised), fields (dict, may be empty)."""
        ...


class ESign(Protocol):
    """Sign a PDF the citizen has already reviewed. The citizen signs on the provider's page; we never see Aadhaar/OTP."""

    mock: bool

    async def create_request(
        self, pdf: bytes, file_name: str, signer_identifier: str, reason: str, reference_id: str
    ) -> AdapterResult:
        """data: document_id, status, signing_url (None when the provider notifies the signer itself)."""
        ...

    async def get_status(self, document_id: str) -> AdapterResult:
        """data: status (normalised)."""
        ...

    async def download_signed(self, document_id: str) -> AdapterResult:
        """data: pdf (bytes). Only valid once the status is completed."""
        ...


class UMANG(Protocol):
    async def list_services(self, query: str) -> AdapterResult: ...


class Messenger(Protocol):
    channel: str

    async def send(self, to: str, text: str, subject: str = "Red Tape Navigator") -> AdapterResult: ...


@dataclass
class Integrations:
    digilocker: DigiLocker
    esign: ESign
    umang: UMANG
    messengers: dict[str, Messenger]
    mode: str  # "mock" | "real"
