"""City-specific fee wording must come only from an official table and must not leak to other cities."""
from app.kb.seed_loader import seed_drafts


def fee(key: str):
    return next(d for d in seed_drafts() if d.key == key)


def test_hyderabad_trade_fee_states_the_published_table_and_its_limits():
    d = fee("trade_licence:hyderabad:fee")
    assert "Rs 3" in d.text and "Rs 4" in d.text and "Rs 6" in d.text
    assert "does not say whether" in d.text and d.source_url == "https://www.ghmc.gov.in/Trade.aspx"
    assert d.confidence < 0.9  # still flagged for a reviewer


def test_other_cities_keep_the_generic_fee_text():
    d = fee("trade_licence:pune:fee")
    assert "varies by trade category" in d.text and "Rs 3" not in d.text


def test_kolkata_fee_comes_from_the_kmc_chart():
    d = fee("trade_licence:kolkata:fee")
    assert "KMC publishes" in d.text and "2026-27" in d.text
    assert d.confidence < 0.9


def test_delhi_fee_comes_from_the_mcd_health_trade_licence_order():
    d = fee("trade_licence:delhi:fee")
    assert "MCD publishes" in d.text and "28.03.2025" in d.text
    assert d.confidence < 0.9


def test_shops_establishments_fee_for_kolkata_and_delhi_is_sourced():
    k = fee("shops_est:kolkata:fee")
    assert "1963" in k.text and "Rs 250" in k.text and k.confidence < 0.9
    d = fee("shops_est:delhi:fee")
    assert "free of cost" in d.text and d.confidence < 0.9


def test_hyderabad_shops_establishments_fee_is_sourced():
    h = fee("shops_est:hyderabad:fee")
    assert "Telangana Labour Department" in h.text and "Rs 10,000" in h.text and h.confidence < 0.9


def test_chennai_shops_establishments_fee_is_sourced():
    c = fee("shops_est:chennai:fee")
    assert "G.O. Ms. No. 55" in c.text and "Rs 100" in c.text and c.confidence < 0.9


def test_maharashtra_fire_fee_states_the_act_structure_without_inventing_rates():
    for city in ("mumbai", "pune"):
        f = fee(f"fire_noc:{city}:fee")
        assert "section 11" in f.text and "Schedule II" in f.text and f.confidence < 0.9
        assert "Rs" not in f.text


def test_mumbai_trade_fee_comes_from_the_mcgm_section_394_schedule():
    m = fee("trade_licence:mumbai:fee")
    assert "Section 394" in m.text and "Rs 47,320" in m.text and "Rs 3,590" in m.text and m.confidence < 0.9


def test_pollution_rule_mentions_the_white_category_intimation():
    from app.kb.catalog import LICENCES

    why = LICENCES["pollution_consent"]["why"]
    assert "White category" in why and "intimation" in why


def test_shops_establishments_fees_for_maharashtra_karnataka_and_gujarat():
    m = fee("shops_est:mumbai:fee")
    assert "no registration fee is prescribed" in m.text and "Form F" in m.text and fee("shops_est:pune:fee").text.split(": ", 1)[1] == m.text.split(": ", 1)[1]
    k = fee("shops_est:bengaluru:fee")
    assert "Rs 405" in k.text and "Rs 1,01,250" in k.text and "e-Karmika" in k.text
    for city in ("ahmedabad", "surat"):
        g = fee(f"shops_est:{city}:fee")
        assert "Rs 2,500" in g.text and "Rs 5,000" in g.text and "Act 1 of 2026" in g.text
    assert all(fee(f"shops_est:{c}:fee").confidence < 0.9 for c in ("mumbai", "pune", "bengaluru", "ahmedabad", "surat"))


def test_pollution_consent_fees_for_karnataka_tamil_nadu_telangana_and_gujarat():
    assert "26 October 2021" in fee("pollution_consent:bengaluru:fee").text
    assert "G.O. (Ms) No. 40" in fee("pollution_consent:chennai:fee").text
    assert "fee calculator" in fee("pollution_consent:hyderabad:fee").text
    for city in ("ahmedabad", "surat"):
        assert "17 October 2018" in fee(f"pollution_consent:{city}:fee").text
    assert fee("pollution_consent:bengaluru:fee").confidence < 0.9



def test_pollution_consent_keeps_the_national_entry_for_cities_outside_the_pack():
    from app.agent.planner import scope_for

    assert scope_for("pollution_consent", "Nagpur") == "national"
    assert scope_for("pollution_consent", "Chennai") == "chennai"
    assert scope_for("trade_licence", "Nagpur") is None
    assert "Central / State Pollution Control Board" in fee("pollution_consent:national:authority").text


def test_delhi_fire_certificate_validity_comes_from_the_dfs_faq():
    from app.kb.seed_loader import seed_drafts

    t = next(d for d in seed_drafts() if d.key == "fire_noc:delhi:timeline")
    assert "Rule 35" in t.text and "5 years for residential" in t.text and "Form I" in t.text and t.confidence < 0.9
    assert t.source_url == "https://dfs.delhi.gov.in/"


def test_clinic_registration_names_each_pilot_state_law_where_a_source_was_found():
    from app.kb.seed_loader import seed_drafts

    drafts = {d.key: d for d in seed_drafts()}
    req = lambda city: drafts[f"clinical_registration:{city}:requirement"].text  # noqa: E731
    assert "Act IV of 2017" in req("kolkata")
    assert "Nursing Homes Registration Act, 1953" in req("delhi")
    assert "Bombay Nursing Homes Registration Act, 1949" in req("mumbai") and req("pune") == req("mumbai").replace("Mumbai", "Pune")
    assert "Karnataka Private Medical Establishments Act, 2007" in req("bengaluru")
    for city in ("chennai", "hyderabad", "ahmedabad", "surat"):
        assert "state's own law and health authority apply" in req(city)
    assert drafts["clinical_registration:delhi:authority"].source_url == "https://dgehs.delhi.gov.in/dghs/nhc/actsrules"


def test_maharashtra_liquor_fee_is_the_2026_gazette_schedule():
    for city in ("mumbai", "pune"):
        f = fee(f"liquor_licence:{city}:fee")
        assert "18 February 2026" in f.text and "Rs 17,33,700" in f.text and "Rs 10,43,900" in f.text and f.confidence < 0.9

