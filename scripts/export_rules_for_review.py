"""Export every seeded rule as a spreadsheet a legal/department reviewer can mark up.

  python scripts/export_rules_for_review.py docs/RULES_REVIEW_EXPORT.csv

Columns: the rule, its official source URL, our confidence, and EMPTY reviewer columns (decision / corrected text /
note / reviewer / date). Every row is exported as UNVERIFIED: only an officer's sign-off in the officer console
(`/en/staff`, audited) changes a rule's status; this file is only a convenient offline worksheet.
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.kb.seed_loader import seed_drafts  # noqa: E402

COLUMNS = ["key", "licence", "scope", "category", "rule_text", "official_source_url", "confidence", "status",
           "reviewer_decision (verified/corrected/rejected)", "corrected_text", "reviewer_note", "reviewer", "review_date"]


def rows():
    for d in sorted(seed_drafts(), key=lambda x: x.key):
        licence, scope, _ = d.key.split(":")
        yield [d.key, licence, scope, d.category, d.text, d.source_url, f"{d.confidence:.2f}", "UNVERIFIED - verify with the authority", "", "", "", "", ""]


def main(path: str) -> int:
    with open(path, "w", encoding="utf-8-sig", newline="") as f:  # BOM so Excel opens UTF-8 correctly
        w = csv.writer(f)
        w.writerow(COLUMNS)
        n = 0
        for r in rows():
            w.writerow(r)
            n += 1
    print(f"wrote {n} rules to {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "rules_review.csv"))
