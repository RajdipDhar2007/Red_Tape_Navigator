"""Real DigiLocker adapter - STUB. Not implemented: needs government access.

Required to go live: DigiLocker Partner API (Meri Pehchaan / API Setu) - requires MeitY registration, client id/secret, signed requester agreement.
See docs/INTEGRATIONS.md. Until then the factory falls back to the labelled mock.
"""
from app.integrations.interfaces import AdapterResult


class RealDigiLocker:
    def __init__(self, **credentials: str):
        self.credentials = credentials

    def _todo(self) -> AdapterResult:
        raise NotImplementedError("DigiLocker real adapter requires government onboarding; see docs/INTEGRATIONS.md")

    async def list_documents(self, user_ref: str) -> AdapterResult:
        return self._todo()

    async def fetch_document(self, user_ref: str, doc_id: str) -> AdapterResult:
        return self._todo()
