from app.core.config import get_settings
from app.integrations.interfaces import Integrations
from app.integrations.mock import MockDigiLocker, MockESign, MockMessenger, MockUMANG


def get_email_sender():
    """SMTP when configured (any mode), otherwise the labelled mock."""
    s = get_settings()
    if s.smtp_host and s.smtp_from:
        from app.integrations.real.smtp import SmtpEmail

        return SmtpEmail(s.smtp_host, s.smtp_port, s.smtp_username, s.smtp_password, s.smtp_from, s.smtp_starttls)
    return MockMessenger("email")


def get_sms_sender():
    """MSG91 when configured (any mode), otherwise the labelled mock."""
    s = get_settings()
    if s.msg91_authkey and s.msg91_template_id:
        from app.integrations.real.msg91 import Msg91Sms

        return Msg91Sms(s.msg91_authkey, s.msg91_template_id, s.msg91_text_var)
    return MockMessenger("sms")


def _digio_client():
    from app.integrations.real.digio import DigioClient

    s = get_settings()
    return DigioClient(s.digio_client_id, s.digio_client_secret, s.digio_env)


def get_esign():
    """Digio when credentials are configured (any mode), otherwise the labelled mock."""
    if get_settings().digio_configured:
        from app.integrations.real.digio import DigioESign

        return DigioESign(_digio_client())
    return MockESign()


def get_digilocker():
    if get_settings().digio_configured:
        from app.integrations.real.digio import DigioDigiLocker

        return DigioDigiLocker(_digio_client(), get_settings().digio_digilocker_template)
    return MockDigiLocker()


def get_integrations() -> Integrations:
    """Mock unless INTEGRATIONS_MODE=real AND credentials exist. Real adapters are stubs until onboarding is done."""
    s = get_settings()
    if s.integrations_mode == "real":  # pragma: no cover - needs credentials
        from app.integrations.real.messaging import RealMessenger
        from app.integrations.real.umang import RealUMANG

        return Integrations(get_digilocker(), get_esign(), RealUMANG(), {"whatsapp": RealMessenger("whatsapp"), "sms": get_sms_sender(), "email": get_email_sender()}, "real")
    return Integrations(get_digilocker(), get_esign(), MockUMANG(), {"whatsapp": MockMessenger("whatsapp"), "sms": get_sms_sender(), "email": get_email_sender()}, "mock")
