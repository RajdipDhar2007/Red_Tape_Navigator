"""Confidence scoring for claims. Deterministic and explainable."""
from datetime import UTC, datetime

from app.core.config import get_settings


def score(
    *, base: float, official_domain: bool, verified_live: bool, quote_grounded: bool | None = None,
    fetched_at: datetime | None = None, seed: bool = False,
) -> float:
    """base: prior reliability of the claim type. Adjusted by provenance and freshness. Clamped to [0, 0.99]."""
    if not official_domain:
        return 0.0  # claims from non-official sources are never trusted
    s = base
    if verified_live:
        s += 0.1
    if quote_grounded is False:
        s -= 0.4  # LLM statement not found verbatim in the source
    if seed and not verified_live:
        s = min(s, 0.8)
    if fetched_at is not None:
        ts = fetched_at if fetched_at.tzinfo else fetched_at.replace(tzinfo=UTC)
        age = (datetime.now(UTC) - ts).days
        if age > 180:
            s -= 0.15
        elif age > 90:
            s -= 0.05
    return round(max(0.0, min(0.99, s)), 2)


def needs_verification(conf: float) -> bool:
    return conf < get_settings().confidence_threshold
