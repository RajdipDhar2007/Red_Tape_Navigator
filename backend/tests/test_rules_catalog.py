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
    d = fee("trade_licence:mumbai:fee")
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
    assert "depends on number of employees" in fee("shops_est:mumbai:fee").text


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
