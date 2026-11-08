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


class DigiLocker(Protocol):
    async def list_documents(self, user_ref: str) -> AdapterResult: ...
    async def fetch_document(self, user_ref: str, doc_id: str) -> AdapterResult: ...


class ESign(Protocol):
    async def request_signature(self, document_sha256: str, signer_ref: str) -> AdapterResult: ...


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
