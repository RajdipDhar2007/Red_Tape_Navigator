"""Common business types: each gets the right checklist or an honest regulator note, never the wrong shop checklist."""
import pytest

from app.agent.intake import parse_goal_rules
from app.kb.seed_loader import seed_drafts


def parsed(goal: str):
    return parse_goal_rules(goal)


@pytest.mark.parametrize("goal,activity", [
    ("I want to open a gift shop in Kolkata", "gift_shop"), ("start a toy store in Pune", "toy_shop"),
    ("open a furniture showroom in Delhi", "furniture_shop"), ("I want to open a florist in Mumbai", "florist"),
    ("open a xerox and photocopy shop in Kolkata", "repair_shop"), ("start a cyber cafe in Chennai", "repair_shop"),
    ("open a supermarket in Hyderabad", "grocery_store"), ("I want to open a gold shop in Kolkata", "jewellery"),
    ("start a jewellery store in Mumbai", "jewellery"), ("open a restaurant near the bank in Kolkata", "restaurant"),
])
def test_ordinary_types_map_to_the_right_checklist(goal, activity):
    p = parsed(goal)
    assert p.activity == activity and p.regulated is None and not p.clarifying_question


@pytest.mark.parametrize("goal,sector,mode", [
    ("I want to open a ration shop in Kolkata", "ration", "authorised"),
    ("open a fair price shop in Pune", "ration", "authorised"),
    ("open a firecracker shop in Hyderabad", "firecrackers", "regulated"),
    ("start a pesticide and fertiliser shop in Ahmedabad", "agri_inputs", "regulated"),
    ("I want to open a bank in Kolkata", "bank", "regulated"), ("open a post office in Pune", "postal", "operated"),
    ("start a taxi service in Bengaluru", "transport", "regulated"), ("open a money changer in Mumbai", "forex", "regulated"),
])
def test_regulated_types_are_recognised_even_when_the_word_shop_is_present(goal, sector, mode):
    p = parsed(goal)
    assert p.regulated["sector"] == sector and p.regulated["mode"] == mode
    assert p.activity == "general_business" and not p.clarifying_question  # baseline premises checklist, no second question


def test_regulated_type_without_a_location_asks_only_for_the_location():
    p = parsed("I want to open a ration shop")
    assert p.regulated["sector"] == "ration" and p.activity is None and "city" in p.clarifying_question.lower()


def test_bis_hallmark_rules_are_seeded_with_the_official_source():
    claims = {d.key: d for d in seed_drafts() if d.key.startswith("bis_hallmark:")}
    assert set(claims) == {f"bis_hallmark:national:{k}" for k in ("requirement", "authority", "fee", "timeline", "documents", "form_link")}
    fee = claims["bis_hallmark:national:fee"]
    assert "no fee" in fee.text and fee.source_url == "https://www.manakonline.in/" and fee.confidence < 0.9


async def test_gold_shop_session_includes_bis_hallmarking(client, auth):
    headers, _ = auth
    await client.post("/consent", json={"purpose": "service", "granted": True}, headers=headers)
    s = (await client.post("/sessions", json={"goal": "I want to open a gold shop in Kolkata", "language": "en"}, headers=headers)).json()
    assert s["parsed"]["activity"] == "jewellery"
    plan = (await client.post(f"/sessions/{s['id']}/research", json={}, headers=headers)).json()["plan"]
    steps = [x["licence"] for x in plan["steps"]]
    assert steps[0] == "udyam" and set(steps) == {"udyam", "bis_hallmark", "trade_licence", "shops_est", "gst"}  # order follows dependencies only
    bis = next(x for x in plan["steps"] if x["licence"] == "bis_hallmark")
    assert "BIS" in bis["name"] and bis["claims"]["fee"]["source_url"] == "https://www.manakonline.in/" and "no fee" in bis["claims"]["fee"]["text"]


async def test_ration_shop_session_gets_the_authorisation_note(client, auth):
    headers, _ = auth
    await client.post("/consent", json={"purpose": "service", "granted": True}, headers=headers)
    s = (await client.post("/sessions", json={"goal": "I want to open a ration shop in Kolkata", "language": "en"}, headers=headers)).json()
    plan = (await client.post(f"/sessions/{s['id']}/research", json={}, headers=headers)).json()["plan"]
    assert "State Food and Civil Supplies Department" in plan["note"] and "appointed or authorised" in plan["note"]
    assert plan["regulated"]["mode"] == "authorised" and plan["steps"]
