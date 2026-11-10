"""List rules whose official source has not been re-read recently.

  python scripts/rule_freshness.py              # report; exit 0
  python scripts/rule_freshness.py --strict     # exit 1 if any rule is overdue (> 90 days)

Last-verified date of a rule = the row of backend/config/rule_verified.csv with the longest matching key prefix, else the
baseline date (the day the rule pack was first seeded from the sources listed in docs/RULES_VERIFICATION.md).
Warn after 60 days, overdue after 90.
"""
import csv
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.kb.seed_loader import seed_drafts  # noqa: E402

BASELINE_DATE = date(2026, 11, 8)
WARN_DAYS, OVERDUE_DAYS = 60, 90
REGISTER = ROOT / "backend" / "config" / "rule_verified.csv"


def load_register(path: Path = REGISTER) -> list[tuple[str, date]]:
    rows: list[tuple[str, date]] = []
    if not path.exists():
        return rows
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.reader(f):
            if not r or r[0].startswith("#") or r[0] == "key_prefix":
                continue
            rows.append((r[0], date.fromisoformat(r[1])))
    return rows


def verified_on(key: str, register: list[tuple[str, date]]) -> date:
    matches = [(len(p), d) for p, d in register if key.startswith(p)]
    return max(matches)[1] if matches else BASELINE_DATE


def audit(today: date, register: list[tuple[str, date]] | None = None) -> dict[str, list[tuple[str, int]]]:
    register = load_register() if register is None else register
    out: dict[str, list[tuple[str, int]]] = {"ok": [], "warn": [], "overdue": []}
    for d in sorted(seed_drafts(), key=lambda x: x.key):
        age = (today - verified_on(d.key, register)).days
        out["overdue" if age > OVERDUE_DAYS else "warn" if age > WARN_DAYS else "ok"].append((d.key, age))
    return out


def main(argv: list[str]) -> int:
    res = audit(date.today())
    print(f"rules: {sum(map(len, res.values()))}  ok: {len(res['ok'])}  warn(>{WARN_DAYS}d): {len(res['warn'])}  overdue(>{OVERDUE_DAYS}d): {len(res['overdue'])}")
    for label in ("overdue", "warn"):
        for key, age in res[label]:
            print(f"{label.upper():8} {age:4}d  {key}")
    return 1 if "--strict" in argv and res["overdue"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
