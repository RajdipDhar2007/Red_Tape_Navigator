"""Value transforms referenced by name from template JSON. `name:arg` for parameterised ones."""
from datetime import date


def parse_transform(spec: str) -> tuple[str, str | None]:
    name, _, arg = spec.partition(":")
    return name, (arg or None)


def _date_ddmmyyyy(v: str, _: str | None) -> str:
    return date.fromisoformat(v).strftime("%d/%m/%Y")


def _rupees(v: str, _: str | None) -> str:
    n = str(int(v))
    head, tail = n[:-3], n[-3:]
    if head:
        parts: list[str] = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        return ",".join(parts) + "," + tail
    return tail


def _checkbox_if(v: str, arg: str | None) -> str:
    return "on" if v == arg else "off"


TRANSFORMS = {
    "identity": lambda v, a: v,
    "upper": lambda v, a: v.upper(),
    "title": lambda v, a: v.title(),
    "date_ddmmyyyy": _date_ddmmyyyy,
    "rupees": _rupees,
    "checkbox_if": _checkbox_if,  # checkbox_if:rented
    "label": lambda v, a: v.replace("_", " ").title(),
    "digits_spaced": lambda v, a: " ".join(v[i : i + 4] for i in range(0, len(v), 4)),
}


def apply(spec: str, value: str) -> str:
    name, arg = parse_transform(spec)
    return TRANSFORMS[name](value, arg)
