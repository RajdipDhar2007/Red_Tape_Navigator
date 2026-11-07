"""Domain allowlist enforced in code. Every outbound fetch must pass `assert_allowed`."""
import ipaddress
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

import yaml

from app.core.config import get_settings


class DomainNotAllowed(ValueError):
    pass


@lru_cache
def load_sources(path: str | None = None) -> dict:
    p = Path(path or get_settings().sources_config)
    if not p.is_absolute() and not p.exists():
        p = Path(__file__).resolve().parents[2] / p
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def allowed_domains() -> list[str]:
    cfg = load_sources()
    return [d.lower() for group in cfg["domains"].values() for d in group]


def assert_allowed(url: str) -> str:
    """Return normalised URL or raise DomainNotAllowed. HTTPS only, no creds, no IPs, no odd ports."""
    u = urlparse(url.strip())
    if u.scheme != "https":
        raise DomainNotAllowed("only https URLs are allowed")
    if u.username or u.password:
        raise DomainNotAllowed("credentials in URL are not allowed")
    host = (u.hostname or "").lower().rstrip(".")
    if not host:
        raise DomainNotAllowed("missing host")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise DomainNotAllowed("IP literals are not allowed")
    if u.port not in (None, 443):
        raise DomainNotAllowed("non-standard port")
    if not any(host == d or host.endswith("." + d) for d in allowed_domains()):
        raise DomainNotAllowed(f"domain not on official allowlist: {host}")
    return u._replace(fragment="").geturl()


def is_allowed(url: str) -> bool:
    try:
        assert_allowed(url)
        return True
    except DomainNotAllowed:
        return False
