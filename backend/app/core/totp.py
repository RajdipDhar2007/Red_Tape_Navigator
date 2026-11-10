"""RFC 6238 time-based one-time passwords (SHA-1, 6 digits, 30 s), implemented with the standard library, plus recovery codes."""
import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

STEP = 30
DIGITS = 6
WINDOW = 1  # accept one step either side for clock drift


def new_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def code_at(secret: str, step: int) -> str:
    key = base64.b32decode(secret + "=" * (-len(secret) % 8), casefold=True)
    digest = hmac.new(key, struct.pack(">Q", step), hashlib.sha1).digest()
    off = digest[-1] & 0x0F
    num = (struct.unpack(">I", digest[off:off + 4])[0] & 0x7FFFFFFF) % 10**DIGITS
    return str(num).zfill(DIGITS)


def verify(secret: str, code: str, last_step: int = 0, now: float | None = None) -> int | None:
    """Return the matched time step, or None. A step at or before ``last_step`` is refused (a code works once)."""
    code = (code or "").replace(" ", "")
    if len(code) != DIGITS or not code.isdigit():
        return None
    cur = int((time.time() if now is None else now) // STEP)
    for step in range(cur - WINDOW, cur + WINDOW + 1):
        if step > last_step and hmac.compare_digest(code_at(secret, step), code):
            return step
    return None


def otpauth_uri(secret: str, email: str, issuer: str = "Red Tape Navigator") -> str:
    return f"otpauth://totp/{quote(issuer)}:{quote(email)}?secret={secret}&issuer={quote(issuer)}&digits={DIGITS}&period={STEP}"


def new_recovery_codes(n: int = 8) -> list[str]:
    return [f"{secrets.token_hex(2)}-{secrets.token_hex(2)}-{secrets.token_hex(2)}" for _ in range(n)]


def hash_recovery(code: str) -> str:
    return hashlib.sha256(code.strip().lower().encode()).hexdigest()
