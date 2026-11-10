import importlib.util
from datetime import date, timedelta
from pathlib import Path

_spec = importlib.util.spec_from_file_location("rule_freshness", Path(__file__).resolve().parents[2] / "scripts" / "rule_freshness.py")
rf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rf)


def test_fresh_rules_are_ok():
    res = rf.audit(rf.BASELINE_DATE + timedelta(days=1), [])
    assert res["warn"] == [] and res["overdue"] == [] and res["ok"]


def test_old_rules_are_overdue_and_strict_fails(monkeypatch):
    res = rf.audit(rf.BASELINE_DATE + timedelta(days=91), [])
    assert res["overdue"] and not res["ok"]
    monkeypatch.setattr(rf, "date", type("D", (date,), {"today": classmethod(lambda cls: rf.BASELINE_DATE + timedelta(days=91))}))
    assert rf.main(["--strict"]) == 1 and rf.main([]) == 0


def test_register_uses_longest_prefix():
    reg = [("gst", date(2026, 12, 1)), ("gst:national", date(2027, 1, 1))]
    assert rf.verified_on("gst:national:fee", reg) == date(2027, 1, 1)
    assert rf.verified_on("gst:kolkata:fee", reg) == date(2026, 12, 1)
    assert rf.verified_on("fssai:x:y", reg) == rf.BASELINE_DATE
