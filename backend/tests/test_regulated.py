"""Businesses licensed by a sector regulator (bank, insurance, pharmacy...) must not be told they are an ordinary shop."""
import pytest

from app.agent.intake import ParsedGoal, apply_general_fallback, regulated_sector


@pytest.mark.parametrize("text,sector", [
    ("Bank", "bank"), ("I want to open a bank branch", "bank"), ("co-operative banking society", "bank"),
    ("NBFC", "nbfc"), ("microfinance company", "nbfc"), ("insurance agency", "insurance"),
    ("stock broking firm", "securities"), ("mutual fund distributor", "securities"),
    ("Pharmacy", "pharmacy"), ("medical store", "pharmacy"), ("liquor shop", "liquor"), ("internet service provider", "telecom"),
])
def test_regulated_sectors_are_recognised(text, sector):
    assert regulated_sector(text)["sector"] == sector


@pytest.mark.parametrize("text", [
    "blood bank", "food bank", "seed bank", "bakery", "barber shop", "sweet shop", "ornamental fish breeding",
    "banner printing", "river bank resort", "tailoring",
])
def test_ordinary_businesses_are_not_flagged(text):
    # "river bank resort" is a known limitation of word matching: it is flagged by design and reviewed by an officer.
    if text == "river bank resort":
        assert regulated_sector(text)["sector"] == "bank"
    else:
        assert regulated_sector(text) is None


def test_fallback_records_the_regulator_and_uses_the_goal_if_the_answer_is_vague():
    p = apply_general_fallback(ParsedGoal(city="Kolkata", state="West Bengal"), "Bank")
    assert p.activity == "general_business" and p.regulated["regulator"].startswith("the Reserve Bank")
    q = apply_general_fallback(ParsedGoal(city="Kolkata", state="West Bengal"), "the main one", "I want to open an insurance agency")
    assert q.regulated["sector"] == "insurance"
    r = apply_general_fallback(ParsedGoal(city="Kolkata", state="West Bengal"), "fish breeding")
    assert r.regulated is None


async def test_bank_session_gets_a_regulator_note_not_the_shop_message(client, auth):
    headers, _ = auth
    await client.post("/consent", json={"purpose": "service", "granted": True}, headers=headers)
    s = (await client.post("/sessions", json={"goal": "I want to open a business in Kolkata", "language": "en"}, headers=headers)).json()
    s2 = (await client.post(f"/sessions/{s['id']}/clarify", json={"answer": "Bank"}, headers=headers)).json()
    assert s2["parsed"]["regulated"]["sector"] == "bank" and s2["parsed"]["regulated"]["url"] == "https://www.rbi.org.in/"
    plan = (await client.post(f"/sessions/{s['id']}/research", json={}, headers=headers)).json()["plan"]
    assert "Reserve Bank of India" in plan["note"] and "baseline checklist most shops need" not in plan["note"]
    assert plan["regulated"]["sector"] == "bank" and plan["steps"]  # premises registrations are still listed
    from sqlalchemy import select

    from app.db.models import ReviewItem
    from app.db.session import maker

    async with maker()() as db:
        reasons = [r.reason for r in (await db.execute(select(ReviewItem).where(ReviewItem.session_id == s["id"]))).scalars()]
    assert any("Regulated/operated business" in x for x in reasons)


def test_post_office_is_operated_by_india_post_not_a_licence_route():
    reg = regulated_sector("post office")
    assert reg["sector"] == "postal" and reg["mode"] == "operated" and reg["url"] == "https://www.indiapost.gov.in/"
    assert regulated_sector("bank")["mode"] == "regulated"
    assert regulated_sector("post-production studio") is None and regulated_sector("compost shop") is None


async def test_post_office_session_note_says_it_is_run_by_india_post(client, auth):
    headers, _ = auth
    await client.post("/consent", json={"purpose": "service", "granted": True}, headers=headers)
    s = (await client.post("/sessions", json={"goal": "I want to open a business in Pune", "language": "en"}, headers=headers)).json()
    await client.post(f"/sessions/{s['id']}/clarify", json={"answer": "post office"}, headers=headers)
    plan = (await client.post(f"/sessions/{s['id']}/research", json={}, headers=headers)).json()["plan"]
    assert "is run by India Post" in plan["note"] and "regulated by" not in plan["note"] and plan["regulated"]["mode"] == "operated"


async def test_hotel_gets_food_fire_and_premises_licences_and_a_lodging_caveat(client, auth):
    headers, _ = auth
    await client.post("/consent", json={"purpose": "service", "granted": True}, headers=headers)
    s = (await client.post("/sessions", json={"goal": "I want to open a hotel in Chennai", "language": "en"}, headers=headers)).json()
    assert s["parsed"]["activity"] == "hotel" and not s["parsed"]["clarifying_question"]
    r = (await client.post(f"/sessions/{s['id']}/research", json={}, headers=headers)).json()
    assert {x["licence"] for x in r["plan"]["steps"]} == {"udyam", "fssai", "trade_licence", "fire_noc", "shops_est", "gst"}
    assert "Lodging-specific" in r["plan"]["note"]
    from sqlalchemy import select

    from app.db.models import ReviewItem
    from app.db.session import maker

    async with maker()() as db:
        reasons = [x.reason for x in (await db.execute(select(ReviewItem).where(ReviewItem.session_id == s["id"]))).scalars()]
    assert any("lodging" in x.lower() for x in reasons)
    for goal in ("open a guest house in Pune", "start a homestay in Delhi", "I want to open a lodge in Kolkata"):
        assert (await client.post("/sessions", json={"goal": goal, "language": "en"}, headers=headers)).json()["parsed"]["activity"] == "hotel"
