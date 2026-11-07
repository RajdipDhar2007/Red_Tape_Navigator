import uuid
from datetime import UTC, datetime, timedelta

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
ROLES = ("citizen", "csc_operator", "reviewer", "admin")


def hash_password(p: str) -> str:
    return pwd.hash(p)


def verify_password(p: str, h: str) -> bool:
    return pwd.verify(p, h)


def _now() -> datetime:
    return datetime.now(UTC)


def create_token(sub: str, role: str, kind: str) -> tuple[str, str, datetime]:
    s = get_settings()
    exp = _now() + (
        timedelta(minutes=s.access_token_minutes) if kind == "access" else timedelta(days=s.refresh_token_days)
    )
    jti = uuid.uuid4().hex
    payload = {"sub": sub, "role": role, "typ": kind, "jti": jti, "exp": exp, "iat": _now()}
    if s.oidc_audience:
        payload["aud"] = s.oidc_audience
    return jwt.encode(payload, s.secret_key, algorithm="HS256"), jti, exp


def decode_token(token: str, kind: str) -> dict:
    s = get_settings()
    kwargs = {"audience": s.oidc_audience} if s.oidc_audience else {"options": {"verify_aud": False}}
    data = jwt.decode(token, s.secret_key, algorithms=["HS256"], **kwargs)
    if data.get("typ") != kind:
        raise jwt.InvalidTokenError("wrong token type")
    return data
