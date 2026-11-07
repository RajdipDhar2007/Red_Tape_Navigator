"""End-to-end smoke test of the demo scenario against a RUNNING stack (used by `make smoke` and CI compose job).

  python scripts/smoke_demo.py http://localhost:8000

Walks: register -> consent -> goal -> research -> interview -> review -> confirm -> download -> checklist.
Exits non-zero on any deviation. Uses only httpx.
"""
import sys
import uuid

import httpx

ANSWERS = {
    "applicant_name": "Asha Roy", "father_name": "Ravi Roy", "dob": "14/03/1990", "gender": "female", "social_category": "general",
    "aadhaar": "210000000007", "pan": "ABCPE1234F", "mobile": "9876543210", "email": "asha@example.com",
    "residence_address": "12 Park Street Kolkata", "residence_pincode": "700016", "business_name": "Sweet Crumbs Bakery",
    "organisation_type": "proprietorship", "date_of_commencement": "01/01/2027", "food_products": "Bread, cakes",
    "num_employees": "3", "annual_turnover": "900000", "investment_amount": "400000", "premises_address": "5 College Street Kolkata",
    "premises_pincode": "700073", "premises_ownership": "rented", "premises_area_sqft": "350",
    "bank_account_number": "123456789012", "bank_ifsc": "SBIN0001234",
}


def check(cond: bool, msg: str) -> None:
    if not cond:
        print(f"SMOKE FAIL: {msg}")
        sys.exit(1)
    print(f"ok  {msg}")


def main(base: str) -> None:
    c = httpx.Client(base_url=base, timeout=60)
    ready = c.get("/ready")
    check(ready.status_code == 200 and ready.json()["database"], "api ready, database reachable")
    tok = c.post("/auth/register", json={"email": f"smoke-{uuid.uuid4().hex[:10]}@example.com", "password": "Smoke-" + uuid.uuid4().hex}).json()
    h = {"Authorization": f"Bearer {tok['access_token']}"}
    check(c.post("/consent", json={"purpose": "service", "granted": True}, headers=h).status_code == 201, "consent recorded")
    s = c.post("/sessions", json={"goal": "I want to open a small bakery in Kolkata", "language": "en"}, headers=h).json()
    sid = s["id"]
    check(s["parsed"]["city"] == "Kolkata" and s["parsed"]["activity"] == "bakery", "goal parsed (bakery, Kolkata)")
    r = c.post(f"/sessions/{sid}/research", json={}, headers=h).json()
    steps = [x["licence"] for x in r["plan"]["steps"]]
    check(steps[:3] == ["udyam", "fssai", "trade_licence"], f"ordered plan {steps}")
    check(all(x["source_url"] and x["content_hash"] for x in r["claims"]) and r["claims"], "every claim has a citation")
    asked: list[str] = []
    for _ in range(40):
        st = c.get(f"/sessions/{sid}/interview", headers=h).json()
        if not st["questions"]:
            break
        keys = [q["key"] for q in st["questions"]]
        if set(keys) & set(asked):
            check(False, f"question asked twice: {keys}")
        asked += keys
        res = c.post(f"/sessions/{sid}/interview", json={"answers": {k: ANSWERS[k] for k in keys}}, headers=h).json()
        if res["errors"]:
            check(False, f"answers rejected: {res['errors']}")
    check(st["complete"], "interview complete (only missing fields asked)")
    check(c.get(f"/sessions/{sid}/forms/fssai_form_a/download", headers=h).status_code == 403, "download blocked before review consent")
    rv = c.get(f"/sessions/{sid}/review", headers=h).json()
    check(len(rv["forms"]) == 3 and all(f["placeholder"] for f in rv["forms"]), "3 filled forms, clearly marked placeholders")
    check(c.post(f"/sessions/{sid}/review", json={"confirm": True}, headers=h).status_code == 200, "explicit review consent")
    pdf = c.get(f"/sessions/{sid}/forms/fssai_form_a/download", headers=h)
    check(pdf.status_code == 200 and pdf.content[:4] == b"%PDF", "filled PDF downloaded")
    cl = c.get(f"/sessions/{sid}/submission-checklist", headers=h).json()
    check("never submits" in cl["important"], "submission checklist: citizen submits, not the system")
    print("SMOKE PASSED")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000")
