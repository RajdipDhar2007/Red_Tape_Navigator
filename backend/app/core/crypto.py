"""Field-level encryption and log redaction for sensitive values (Aadhaar, PAN)."""
import base64
import hashlib
import re

from cryptography.fernet import Fernet

from app.core.config import get_settings

SENSITIVE_KEYS = {"aadhaar", "pan", "aadhaar_number", "pan_number"}
_AADHAAR = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
_PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")


def _fernet() -> Fernet:
    s = get_settings()
    if s.field_encryption_key:
        return Fernet(s.field_encryption_key.encode())
    # dev fallback derived from SECRET_KEY (rejected in prod by get_settings)
    digest = hashlib.sha256(s.secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()


def mask(value: str) -> str:
    return "*" * max(len(value) - 4, 0) + value[-4:]


def redact_text(text: str) -> str:
    text = _AADHAAR.sub("[AADHAAR-REDACTED]", text)
    return _PAN.sub("[PAN-REDACTED]", text)


def redact(obj):
    """Recursively redact sensitive keys/values for logs and audit detail."""
    if isinstance(obj, dict):
        return {k: ("[REDACTED]" if k.lower() in SENSITIVE_KEYS else redact(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(v) for v in obj]
    if isinstance(obj, str):
        return redact_text(obj)
    return obj
