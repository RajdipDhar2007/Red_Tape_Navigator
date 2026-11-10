"""Plans and prices come from ``backend/config/pricing.yaml`` (placeholder prices, owner-editable). Nothing else hard-codes a price."""
from functools import lru_cache
from pathlib import Path

import yaml

PRICING_FILE = Path(__file__).resolve().parents[2] / "config" / "pricing.yaml"
INTERVALS = ("month", "year")


@lru_cache
def load_pricing() -> dict:
    return yaml.safe_load(PRICING_FILE.read_text(encoding="utf-8"))


def plans() -> dict[str, dict]:
    return load_pricing()["plans"]


def price_paise(plan: str, interval: str) -> int:
    """Price excluding GST, in paise. Raises KeyError/ValueError for unknown plan or interval."""
    if interval not in INTERVALS:
        raise ValueError("interval must be month or year")
    return int(plans()[plan][f"price_{interval}"]) * 100


def features_of(plan: str) -> set[str]:
    return set(plans().get(plan, plans()["free"])["features"])


def limits_of(plan: str) -> dict:
    return dict(plans().get(plan, plans()["free"])["limits"])


def grace_days() -> int:
    return int(load_pricing().get("grace_days_after_failed_payment", 7))


def public_plans() -> list[dict]:
    p = load_pricing()
    return [
        {"id": pid, "name": v["name"], "price_month": v["price_month"], "price_year": v["price_year"], "limits": v["limits"],
         "features": v["features"], "placeholder_price": bool(p.get("placeholder"))}
        for pid, v in p["plans"].items()
    ]
