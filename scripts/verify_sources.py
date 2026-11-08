"""Check every source URL cited by the curated rules pack against the live official site.

  python scripts/verify_sources.py            # report only (exit 1 if any source is unreachable/blocked)
  python scripts/verify_sources.py --json out.json

For each distinct source URL it fetches the page through the project's own guarded fetcher (allowlist, robots.txt,
rate limit, captcha/login detection) and, for each claim that cites it, reports whether the numbers quoted in the claim
(fees, days, years) appear in the live page text. A claim whose numbers are NOT found stays "needs human verification":
this tool never edits the rules pack and never marks anything verified; officers do that in the review queue.
"""
import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.kb.seed_loader import seed_drafts  # noqa: E402
from app.scraping.fetcher import HumanHandoffRequired, RobotsDisallowed, fetch_page  # noqa: E402

NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def numbers_in(text: str) -> set[str]:
    return {n.replace(",", "") for n in NUM.findall(text)}


async def check(url: str) -> dict:
    try:
        page = await fetch_page(url)
        return {"url": url, "status": "ok", "text": page.text, "chars": len(page.text)}
    except HumanHandoffRequired:
        return {"url": url, "status": "needs_human", "text": ""}
    except RobotsDisallowed:
        return {"url": url, "status": "robots_disallowed", "text": ""}
    except Exception as exc:  # noqa: BLE001 - report every failure kind
        return {"url": url, "status": f"error:{type(exc).__name__}", "text": ""}


async def main(json_out: str | None) -> int:
    claims = seed_drafts()
    by_url: dict[str, list] = {}
    for c in claims:
        by_url.setdefault(c.source_url, []).append(c)
    report, bad = [], 0
    for url, cs in sorted(by_url.items()):
        r = await check(url)
        page_nums = numbers_in(r["text"])
        entry = {"url": url, "status": r["status"], "claims": len(cs), "claims_with_numbers_found": 0, "claims_unconfirmed": [],
                 "numeric_claims": 0}
        for c in cs:
            claim_nums = numbers_in(c.text) - {"1", "2", "3"}
            entry["numeric_claims"] += bool(claim_nums)
            if r["status"] == "ok" and claim_nums and claim_nums <= page_nums:
                entry["claims_with_numbers_found"] += 1
            else:
                entry["claims_unconfirmed"].append(c.key)
        if r["status"] != "ok":
            bad += 1
        report.append(entry)
        print(f"{entry['status']:<28} {url}  claims={entry['claims']} confirmed_numbers={entry['claims_with_numbers_found']}")
    if json_out:
        Path(json_out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    total = sum(e["claims"] for e in report)
    numeric = sum(e["numeric_claims"] for e in report)
    confirmed = sum(e["claims_with_numbers_found"] for e in report)
    print(f"\n{len(report)} sources, {bad} unreachable/blocked.")
    print(f"{total} claims: {numeric} quote a number (those can be checked automatically), {total - numeric} are qualitative "
          f"(\"confirm with the authority\" wording) and need a human reviewer.")
    print(f"{confirmed}/{numeric} numeric claims have their numbers on the live page. Nothing is marked verified by this tool.")
    return 1 if bad else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", dest="json_out")
    sys.exit(asyncio.run(main(ap.parse_args().json_out)))
