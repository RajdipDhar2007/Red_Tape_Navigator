"""Clearly-labelled mock adapters. They never touch real services and never fake a real submission."""
from app.integrations.interfaces import AdapterResult

DEMO = "Demo mode: simulated"


class MockDigiLocker:
    async def list_documents(self, user_ref: str) -> AdapterResult:
        return AdapterResult(True, {"documents": [{"id": "demo-aadhaar", "type": "Aadhaar (demo)"}, {"id": "demo-pan", "type": "PAN (demo)"}]}, True, f"{DEMO} DigiLocker")

    async def fetch_document(self, user_ref: str, doc_id: str) -> AdapterResult:
        # Demo data only: clearly fake identity values.
        data = {"applicant_name": "Demo Citizen", "residence_address": "1 Demo Street, Demo Locality", "residence_pincode": "700001"}
        return AdapterResult(True, {"doc_id": doc_id, "fields": data}, True, f"{DEMO} DigiLocker fetch (values are placeholders)")


class MockESign:
    async def request_signature(self, document_sha256: str, signer_ref: str) -> AdapterResult:
        return AdapterResult(True, {"signature": "SIMULATED-NOT-LEGALLY-VALID", "document_sha256": document_sha256, "legally_valid": False}, True, f"{DEMO} e-Sign")


class MockUMANG:
    async def list_services(self, query: str) -> AdapterResult:
        return AdapterResult(True, {"services": [{"name": f"Demo UMANG service matching '{query[:40]}'"}]}, True, f"{DEMO} UMANG")


class MockMessenger:
    OUTBOX: list[dict] = []

    def __init__(self, channel: str):
        self.channel = channel

    async def send(self, to: str, text: str) -> AdapterResult:
        MockMessenger.OUTBOX.append({"channel": self.channel, "to": to, "text": text})
        return AdapterResult(True, {"queued": True}, True, f"{DEMO} {self.channel} (not actually sent)")
