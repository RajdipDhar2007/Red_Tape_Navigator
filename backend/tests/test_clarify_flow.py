"""The follow-up question flow: a city answer must never become the business type, and common typos must still match."""
import pytest

from app.agent.intake import ParsedGoal, asked_for_business_type, parse_goal_rules


@pytest.mark.parametrize("goal,activity", [
    ("resturent", "restaurant"), ("I want to open a restaurent", "restaurant"), ("restarant", "restaurant"), ("resteraunt in Kolkata", "restaurant"),
    ("cakes", "bakery"), ("I want to sell cake", "bakery"), ("bakary", "bakery"), ("pastry shop", "bakery"),
    ("saloon", "beauty_parlour"), ("grocary store", "grocery_store"), ("cafee", "cafe"),
])
def test_common_typos_and_short_words_find_the_business(goal, activity):
    assert parse_goal_rules(goal).activity == activity


def test_typo_list_does_not_turn_unrelated_words_into_businesses():
    for goal in ("garbage collection in Kolkata", "I want to open a restful retreat", "baking soda"):
        assert parse_goal_rules(goal).activity in (None, "bakery", "retail_shop", "hotel")  # never a surprising one
    assert parse_goal_rules("garbage collection in Kolkata").activity is None


def test_the_answer_is_only_a_business_type_when_that_was_the_question():
    assert not asked_for_business_type(ParsedGoal().model_dump())  # nothing known: the question was the place
    assert not asked_for_business_type(ParsedGoal(city="Kolkata").model_dump())  # state still missing
    assert asked_for_business_type(ParsedGoal(city="Kolkata", state="West Bengal").model_dump())
    assert not asked_for_business_type(ParsedGoal(city="Kolkata", state="West Bengal", activity="bakery").model_dump())


async def _session(client, auth, goal):
    headers, _ = auth
    await client.post("/consent", json={"purpose": "service", "granted": True}, headers=headers)
    return headers, (await client.post("/sessions", json={"goal": goal, "language": "en"}, headers=headers)).json()


async def test_misspelt_business_then_city_gets_a_real_restaurant_plan(client, auth):
    headers, s = await _session(client, auth, "resturent")
    assert s["parsed"]["activity"] == "restaurant" and "city" in s["parsed"]["clarifying_question"].lower()
    s2 = (await client.post(f"/sessions/{s['id']}/clarify", json={"answer": "kolkata"}, headers=headers)).json()
    assert s2["parsed"]["activity"] == "restaurant" and s2["parsed"]["city"] == "Kolkata" and not s2["parsed"]["clarifying_question"]
    assert not s2["parsed"].get("activity_label")  # the city was never taken for the business type
    plan = (await client.post(f"/sessions/{s['id']}/research", json={}, headers=headers)).json()["plan"]
    assert "fssai" in [x["licence"] for x in plan["steps"]] and "baseline checklist" not in (plan.get("note") or "")


async def test_city_answer_to_an_unknown_business_asks_what_the_business_is(client, auth):
    headers, s = await _session(client, auth, "I want to start something new")
    s2 = (await client.post(f"/sessions/{s['id']}/clarify", json={"answer": "Kolkata"}, headers=headers)).json()
    assert s2["parsed"]["city"] == "Kolkata" and s2["parsed"]["activity"] is None
    assert "kind of business" in s2["parsed"]["clarifying_question"] and not s2["parsed"].get("activity_label")
    s3 = (await client.post(f"/sessions/{s['id']}/clarify", json={"answer": "ornamental fish breeding"}, headers=headers)).json()
    assert s3["parsed"]["activity"] == "general_business" and s3["parsed"]["activity_label"] == "ornamental fish breeding"
    s4 = (await client.post(f"/sessions/{s['id']}/clarify", json={"answer": "bakery"}, headers=headers)).json()
    assert s4["parsed"]["city"] == "Kolkata"  # still known
