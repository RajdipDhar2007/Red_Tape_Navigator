"""Evaluation harness: golden cases -> licences, ordering, fields, citation coverage, hallucination check.

Run:  python -m evals.run            (exit code 1 when a quality gate fails; used in CI)
Gates: case pass rate >= 0.95, citation coverage == 1.0, hallucination failures == 0.
"""
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

from app.scraping.allowlist import is_allowed

CASES = Path(__file__).with_name("golden_cases.json")
GATES = {"pass_rate": 0.95, "citation_coverage": 1.0, "hallucinations": 0}


def claim_has_citation(c: dict) -> bool:
    return bool(c.get("source_url")) and bool(c.get("content_hash")) and bool(c.get("fetched_at")) and is_allowed(c["source_url"])


def check_claims(claims: list[dict]) -> dict:
    """Hallucination check: any claim without a valid official source fails. Returns coverage stats."""
    cited = [c for c in claims if claim_has_citation(c)]
    return {
        "total": len(claims), "cited": len(cited),
        "coverage": 1.0 if not claims else len(cited) / len(claims),
        "uncited": [c.get("key", "?") for c in claims if not claim_has_citation(c)],
    }


def order_ok(steps: list[dict]) -> bool:
    pos = {s["licence"]: i for i, s in enumerate(steps)}
    return all(pos[d] < pos[s["licence"]] for s in steps for d in s["depends_on"] if d in pos)


async def run_case(db, case: dict) -> dict:
    from app.agent.intake import parse_goal_rules
    from app.agent.research import research
    from app.forms.registry import required_keys_for

    failures: list[str] = []
    parsed = parse_goal_rules(case["goal"], case.get("language", "en"))

    def expect(cond: bool, msg: str) -> None:
        if not cond:
            failures.append(msg)

    expect(bool(parsed.clarifying_question) == case.get("expect_clarify", False), f"clarify={bool(parsed.clarifying_question)}")
    if "expect_city" in case:
        expect(parsed.city == case["expect_city"], f"city={parsed.city}")
    if "expect_state" in case:
        expect(parsed.state == case["expect_state"], f"state={parsed.state}")
    if case.get("expect_no_activity"):
        expect(parsed.activity is None, f"activity={parsed.activity}")

    claims: list[dict] = []
    precision = recall = 1.0
    if parsed.activity and not parsed.clarifying_question:
        res = await research(db, parsed.model_dump())
        steps = res["plan"]["steps"]
        got = [s["licence"] for s in steps]
        want = case.get("expect_licences")
        if want is not None:
            tp = len(set(got) & set(want))
            precision, recall = tp / (len(got) or 1), tp / (len(want) or 1)
            expect(set(got) == set(want), f"licences={sorted(got)}")
        for f in case.get("forbid_licences", []):
            expect(f not in got, f"forbidden licence present: {f}")
        expect(order_ok(steps), "dependency order violated")
        forms = [s["form"] for s in steps if s["form"]]
        req = required_keys_for(forms)
        for f in case.get("expect_fields", []):
            expect(f in req, f"missing required field {f}")
        for f in case.get("forbid_fields", []):
            expect(f not in req, f"unexpected field {f}")
        if "expect_authority" in case:
            texts = " ".join(c["text"] for s in steps for c in s["claims"].values())
            expect(case["expect_authority"] in texts, "expected authority not cited")
        if case.get("expect_municipal_missing"):
            tl = next(s for s in steps if s["licence"] == "trade_licence")
            expect(tl["municipal_data_missing"] and not tl["claims"], "municipal gap not flagged")
        claims = [c for s in steps for c in s["claims"].values()]
        # low-confidence claims must carry the verify flag
        for c in claims:
            if c["confidence"] < 0.6:
                expect(c["needs_verification"], f"low-confidence claim not flagged: {c['key']}")
    stats = check_claims(claims)
    if stats["uncited"]:
        failures.append(f"HALLUCINATION: uncited claims {stats['uncited']}")
    return {"id": case["id"], "passed": not failures, "failures": failures, "precision": precision, "recall": recall,
            "claims": stats["total"], "cited": stats["cited"], "hallucinated": len(stats["uncited"])}


async def run_all(cases: list[dict]) -> dict:
    from app.db.models import Base
    from app.db.session import get_engine, maker, reset_engine

    await reset_engine()
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    results = []
    async with maker()() as db:
        for c in cases:
            results.append(await run_case(db, c))
    await reset_engine()
    n = len(results)
    total = sum(r["claims"] for r in results)
    cited = sum(r["cited"] for r in results)
    summary = {
        "cases": n, "passed": sum(r["passed"] for r in results), "pass_rate": sum(r["passed"] for r in results) / n,
        "citation_coverage": 1.0 if not total else cited / total, "claims_checked": total,
        "hallucinations": sum(r["hallucinated"] for r in results),
        "mean_precision": sum(r["precision"] for r in results) / n, "mean_recall": sum(r["recall"] for r in results) / n,
    }
    summary["gates_passed"] = (
        summary["pass_rate"] >= GATES["pass_rate"] and summary["citation_coverage"] >= GATES["citation_coverage"]
        and summary["hallucinations"] <= GATES["hallucinations"]
    )
    return {"summary": summary, "results": results}


def main() -> int:
    tmp = tempfile.mkdtemp()
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{tmp}/evals.db".replace("\\", "/")
    out = asyncio.run(run_all(json.loads(CASES.read_text(encoding="utf-8"))))
    for r in out["results"]:
        print(("PASS " if r["passed"] else "FAIL ") + r["id"] + ("" if r["passed"] else "  -> " + "; ".join(r["failures"])))
    print(json.dumps(out["summary"], indent=2))
    Path(__file__).with_name("report.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return 0 if out["summary"]["gates_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
