"""Clearly-labelled mock adapters. They never touch real services and never fake a real submission."""
from app.integrations.interfaces import STATUS_COMPLETED, AdapterResult

DEMO = "Demo mode: simulated"


class MockDigiLocker:
    mock = True

    async def start_request(self, customer_identifier: str, customer_name: str, reference_id: str) -> AdapterResult:
        # Demo data only: clearly fake identity values.
        fields = {"applicant_name": "Demo Citizen", "residence_address": "1 Demo Street, Demo Locality", "residence_pincode": "700001"}
        return AdapterResult(True, {"request_id": f"SIMULATED-{reference_id[:8]}", "status": STATUS_COMPLETED, "fields": fields}, True,
                             f"{DEMO} DigiLocker fetch (values are placeholders)")

    async def get_status(self, request_id: str) -> AdapterResult:
        return AdapterResult(True, {"request_id": request_id, "status": STATUS_COMPLETED, "fields": {}}, True, f"{DEMO} DigiLocker")


class MockESign:
    mock = True

    async def create_request(self, pdf: bytes, file_name: str, signer_identifier: str, reason: str, reference_id: str) -> AdapterResult:
        return AdapterResult(True, {"document_id": f"SIMULATED-{reference_id[:8]}", "status": STATUS_COMPLETED, "signing_url": None,
                                    "signature": "SIMULATED-NOT-LEGALLY-VALID", "legally_valid": False}, True, f"{DEMO} e-Sign")

    async def get_status(self, document_id: str) -> AdapterResult:
        return AdapterResult(True, {"document_id": document_id, "status": STATUS_COMPLETED, "legally_valid": False}, True, f"{DEMO} e-Sign")

    async def download_signed(self, document_id: str) -> AdapterResult:
        return AdapterResult(False, {"error": "simulated_signature_has_no_file"}, True, f"{DEMO} e-Sign: no signed file exists")


class MockUMANG:
    async def list_services(self, query: str) -> AdapterResult:
        return AdapterResult(True, {"services": [{"name": f"Demo UMANG service matching '{query[:40]}'"}]}, True, f"{DEMO} UMANG")


class MockMessenger:
    OUTBOX: list[dict] = []

    def __init__(self, channel: str):
        self.channel = channel

    async def send(self, to: str, text: str, subject: str = "Red Tape Navigator") -> AdapterResult:
        MockMessenger.OUTBOX.append({"channel": self.channel, "to": to, "text": text, "subject": subject})
        return AdapterResult(
            True,
            {"queued": True, "smtp_accepted": False, "delivery_status": "queued_mock"},
            True,
            f"{DEMO} {self.channel} (not actually sent)",
        )
