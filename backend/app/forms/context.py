"""Derived (non-asked) values available to form templates, computed from the parsed goal."""
from datetime import date

from app.kb.catalog import ACTIVITIES, CITIES


def build_context(parsed: dict) -> dict[str, str]:
    ctx: dict[str, str] = {}
    city = parsed.get("city")
    if city:
        ctx["city"] = city
        for c in CITIES.values():
            if c["label"].lower() == city.lower():
                ctx["authority"] = c["authority"]
    if parsed.get("state"):
        ctx["state"] = parsed["state"]
    act = parsed.get("activity")
    if act in ACTIVITIES:
        ctx["business_type"] = act
        ctx["business_type_label"] = ACTIVITIES[act]["label"]
    ctx["today"] = date.today().isoformat()
    return ctx
