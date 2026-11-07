"""Real UMANG adapter - STUB. Not implemented: needs government access.

Required to go live: UMANG department onboarding via MeitY/NeGD, API credentials.
See docs/INTEGRATIONS.md. Until then the factory falls back to the labelled mock.
"""
from app.integrations.interfaces import AdapterResult


class RealUMANG:
    def __init__(self, **credentials: str):
        self.credentials = credentials

    def _todo(self) -> AdapterResult:
        raise NotImplementedError("UMANG real adapter requires government onboarding; see docs/INTEGRATIONS.md")

    async def list_services(self, query: str) -> AdapterResult:
        return self._todo()
