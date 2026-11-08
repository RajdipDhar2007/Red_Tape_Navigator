"""Structural checks over the whole catalogue (about 110 business types) and the sourced, state-specific licences."""
import pathlib
import re

import pytest
import yaml

from app.agent.intake import parse_goal_rules
from app.kb.catalog import ACTIVITIES, ACTIVITY_KEYWORDS, CITIES, LICENCES, REGULATED_SECTORS
from app.kb.seed_loader import seed_drafts

REAL_TYPES = [a for a in ACTIVITIES if a != "general_business"]


def test_the_pack_covers_at_least_a_hundred_business_types():
    assert len(REAL_TYPES) >= 100


def test_every_type_uses_only_known_licences_and_has_keywords():
    for a, spec in ACTIVITIES.items():
        assert spec["label"] and spec["licences"], a
        assert all(lic in LICENCES for lic in spec["licences"]), (a, spec["licences"])
        assert len(set(spec["licences"])) == len(spec["licences"]), a
        if a != "general_business":
            assert ACTIVITY_KEYWORDS.get(a), f"{a} has no keywords"


def test_keywords_are_lowercase_and_not_shared_between_types():
    seen: dict[str, str] = {}
    for a, words in ACTIVITY_KEYWORDS.items():
        for w in words:
            assert w == w.lower(), (a, w)
            assert w not in seen or seen[w] == a, f"keyword {w!r} used by both {seen[w]} and {a}"
            seen[w] = a


@pytest.mark.parametrize("activity", REAL_TYPES)
def test_each_type_is_recognised_from_its_own_keywords(activity):
    # every English keyword must resolve to its own type (the longest keyword wins) in a normal sentence
    for kw in (w for w in ACTIVITY_KEYWORDS[activity] if w.isascii()):
        p = parse_goal_rules(f"I want to open a {kw} in Kolkata")
        assert p.activity == activity, f"{kw!r} gave {p.activity}, expected {activity}"


def test_sourced_state_licences_have_all_eight_cities_with_real_content():
    by_city_licences = [lid for lid, lic in LICENCES.items() if lic.get("by_city")]
    assert {"liquor_licence", "drug_licence"} <= set(by_city_licences)
    for lid in by_city_licences:
        entries = LICENCES[lid]["by_city"]
        assert set(entries) == set(CITIES), lid
        for city, e in entries.items():
            for key in ("authority", "url", "fee", "timeline", "documents", "why"):
                assert e.get(key), (lid, city, key)
            assert e["url"].startswith("https://") and isinstance(e["documents"], list)
            assert 0 < e.get("fee_conf", 0.5) < 0.9  # every state entry stays flagged for a reviewer


def _allowlist() -> set[str]:
    out: set[str] = set()

    def walk(x):
        if isinstance(x, str):
            out.add(x)
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(yaml.safe_load(pathlib.Path("config/sources.yaml").read_text(encoding="utf-8")))
    return out


def test_every_claim_source_is_https_and_on_the_allowlist():
    allowed = _allowlist()
    for d in seed_drafts():
        host = re.sub(r"^https://([^/]+)/?.*$", r"\1", d.source_url)
        assert d.source_url.startswith("https://"), d.key
        assert any(host == a or host.endswith("." + a) for a in allowed), f"{host} (claim {d.key}) is not on the allowlist"


def test_state_specific_claims_are_seeded_per_city_with_that_states_authority():
    claims = {d.key: d for d in seed_drafts()}
    assert "Excise Directorate, Government of West Bengal" in claims["liquor_licence:kolkata:authority"].text
    assert "Telangana" in claims["liquor_licence:hyderabad:authority"].text
    assert "Department of Drugs Control" in claims["drug_licence:delhi:authority"].text
    assert "Form 19" in claims["drug_licence:delhi:documents"].text and "Form 19" in claims["drug_licence:pune:documents"].text
    assert all(c.confidence < 0.9 for k, c in claims.items() if k.startswith(("liquor_licence", "drug_licence", "pet_shop")))


def test_regulated_patterns_compile_and_do_not_shadow_real_checklists():
    for info in REGULATED_SECTORS.values():
        re.compile(info["pattern"])
    for a in ("liquor_shop", "pharmacy", "clinic", "hospital", "school", "college", "pet_shop"):
        assert a in ACTIVITIES
    assert not {"liquor", "pharmacy", "clinic", "school"} & set(REGULATED_SECTORS)  # they are real licence checklists now


@pytest.mark.parametrize("goal,activity,must_include", [
    ("open a wine shop in Kolkata", "liquor_shop", "liquor_licence"),
    ("open a medical store in Delhi", "pharmacy", "drug_licence"),
    ("open a pet shop in Pune", "pet_shop", "pet_shop_registration"),
    ("start a coaching centre in Mumbai", "coaching_centre", "coaching_registration"),
    ("open a private clinic in Chennai", "clinic", "clinical_registration"),
    ("open a hospital in Hyderabad", "hospital", "bmw_authorisation"),
    ("open a school in Ahmedabad", "school", "school_recognition"),
    ("open a college in Bengaluru", "college", "college_approval"),
])
async def test_sessions_for_the_named_sectors_get_real_licences_not_a_dead_end(client, auth, goal, activity, must_include):
    headers, _ = auth
    await client.post("/consent", json={"purpose": "service", "granted": True}, headers=headers)
    s = (await client.post("/sessions", json={"goal": goal, "language": "en"}, headers=headers)).json()
    assert s["parsed"]["activity"] == activity and not s["parsed"]["clarifying_question"] and not s["parsed"].get("regulated")
    plan = (await client.post(f"/sessions/{s['id']}/research", json={}, headers=headers)).json()["plan"]
    step = next(x for x in plan["steps"] if x["licence"] == must_include)
    assert step["claims"]["documents"]["source_url"].startswith("https://") and step["claims"]["authority"]["text"]
    assert "cannot list it" not in (plan.get("note") or "")


async def test_liquor_shop_shows_each_states_own_official_rules(client, auth):
    headers, _ = auth
    await client.post("/consent", json={"purpose": "service", "granted": True}, headers=headers)

    async def plan_for(city):
        s = (await client.post("/sessions", json={"goal": f"I want to open a wine shop in {city}", "language": "en"}, headers=headers)).json()
        return (await client.post(f"/sessions/{s['id']}/research", json={}, headers=headers)).json()["plan"]

    def step(plan, lid):
        return next(x for x in plan["steps"] if x["licence"] == lid)

    kolkata = await plan_for("Kolkata")
    assert "Affidavit declaring medical fitness" in step(kolkata, "liquor_licence")["claims"]["documents"]["text"]
    assert "restricted" not in kolkata  # West Bengal has an application route

    for city, phrase in (("Delhi", "only to selected Delhi government undertakings"), ("Ahmedabad", "prohibition state"),
                         ("Chennai", "state marketing corporation (TASMAC)"), ("Mumbai", "ban on grant of new license")):
        p = await plan_for(city)
        assert p["restricted"]["licence"] == "liquor_licence" and phrase in p["restricted"]["text"], city

    hyd = await plan_for("Hyderabad")
    assert "restricted" not in hyd and "Rs 2,00,000" in step(hyd, "liquor_licence")["claims"]["fee"]["text"]


async def test_types_with_extra_permits_say_so_and_queue_an_officer(client, auth):
    headers, _ = auth
    await client.post("/consent", json={"purpose": "service", "granted": True}, headers=headers)
    s = (await client.post("/sessions", json={"goal": "I want to open a meat shop in Kolkata", "language": "en"}, headers=headers)).json()
    plan = (await client.post(f"/sessions/{s['id']}/research", json={}, headers=headers)).json()["plan"]
    assert plan["coverage"] == "specific" and "may also apply" in plan["note"]
    assert "fssai" in [x["licence"] for x in plan["steps"]]


async def test_a_licence_added_after_the_kb_was_seeded_is_loaded_on_demand(client, auth):
    """Regression: an old local database had many claims but none for newer licences, so plans showed empty steps."""
    from sqlalchemy import delete

    from app.db.models import Claim
    from app.db.session import maker

    headers, _ = auth
    await client.post("/consent", json={"purpose": "service", "granted": True}, headers=headers)
    s = (await client.post("/sessions", json={"goal": "I want to open a wine shop in Kolkata", "language": "en"}, headers=headers)).json()
    await client.post(f"/sessions/{s['id']}/research", json={}, headers=headers)  # seeds everything
    async with maker()() as db:
        await db.execute(delete(Claim).where(Claim.key.like("liquor_licence:%")))
        await db.commit()
    plan = (await client.post(f"/sessions/{s['id']}/research", json={}, headers=headers)).json()["plan"]
    step = next(x for x in plan["steps"] if x["licence"] == "liquor_licence")
    assert "Excise Directorate" in step["claims"]["authority"]["text"]
