import json

from evals import run as ev


def test_golden_set_size():
    assert len(json.loads(ev.CASES.read_text(encoding="utf-8"))) >= 20


def test_hallucination_check_is_not_vacuous():
    good = {"key": "a", "source_url": "https://gst.gov.in/", "content_hash": "h" * 64, "fetched_at": "2026-01-01T00:00:00+00:00"}
    for bad in (
        {**good, "source_url": ""}, {**good, "content_hash": ""}, {**good, "fetched_at": None},
        {**good, "source_url": "https://random-blog.example/x"},
    ):
        stats = ev.check_claims([good, bad])
        assert stats["coverage"] == 0.5 and stats["uncited"] == ["a"]
    assert ev.check_claims([good])["coverage"] == 1.0 and ev.check_claims([])["coverage"] == 1.0


def test_order_check_detects_violation():
    steps = [{"licence": "fssai", "depends_on": ["udyam"]}, {"licence": "udyam", "depends_on": []}]
    assert not ev.order_ok(steps) and ev.order_ok(steps[::-1])


async def test_golden_cases_meet_quality_gates(client):
    out = await ev.run_all(json.loads(ev.CASES.read_text(encoding="utf-8")))
    failed = [r for r in out["results"] if not r["passed"]]
    assert not failed, failed
    s = out["summary"]
    assert s["gates_passed"] and s["citation_coverage"] == 1.0 and s["hallucinations"] == 0
