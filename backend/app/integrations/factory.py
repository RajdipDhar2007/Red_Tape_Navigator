from app.core.config import get_settings
from app.integrations.interfaces import Integrations
from app.integrations.mock import MockDigiLocker, MockESign, MockMessenger, MockUMANG


def get_integrations() -> Integrations:
    """Mock unless INTEGRATIONS_MODE=real AND credentials exist. Real adapters are stubs until onboarding is done."""
    s = get_settings()
    if s.integrations_mode == "real":  # pragma: no cover - needs credentials
        from app.integrations.real.digilocker import RealDigiLocker
        from app.integrations.real.esign import RealESign
        from app.integrations.real.messaging import RealMessenger
        from app.integrations.real.umang import RealUMANG

        return Integrations(RealDigiLocker(), RealESign(), RealUMANG(), {c: RealMessenger(c) for c in ("email", "sms", "whatsapp")}, "real")
    return Integrations(MockDigiLocker(), MockESign(), MockUMANG(), {c: MockMessenger(c) for c in ("email", "sms", "whatsapp")}, "mock")
