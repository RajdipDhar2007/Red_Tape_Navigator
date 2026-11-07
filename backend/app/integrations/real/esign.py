"""Real ESign adapter - STUB. Not implemented: needs government access.

Required to go live: ASP licence with a CCA-approved e-Sign Service Provider (e.g. via NSDL/eMudhra), Aadhaar authentication licence (AUA/Sub-AUA), UIDAI approval.
See docs/INTEGRATIONS.md. Until then the factory falls back to the labelled mock.
"""
from app.integrations.interfaces import AdapterResult


class RealESign:
    def __init__(self, **credentials: str):
        self.credentials = credentials

    def _todo(self) -> AdapterResult:
        raise NotImplementedError("ESign real adapter requires government onboarding; see docs/INTEGRATIONS.md")

    async def request_signature(self, document_sha256: str, signer_ref: str) -> AdapterResult:
        return self._todo()
