import pytest

from app.agent.intake import parse_goal_rules


@pytest.mark.parametrize(
    ("goal", "activity"),
    [
        ("मैं कोलकाता में किताब की दुकान खोलना चाहता हूँ", "book_store"),
        ("আমি কলকাতায় ফুলের দোকান খুলতে চাই", "florist"),
        ("मुंबई में गोदाम शुरू करना है", "warehouse"),
        ("আমি কলকাতায় নাপিতের দোকান", "barber_shop"),
    ],
)
def test_hindi_bengali_business_keywords(goal, activity):
    assert parse_goal_rules(goal).activity == activity


@pytest.mark.parametrize(
    ("goal", "activity"),
    [
        ("I want to open a spa centre in Mumbai", "spa_centre"),
        ("open a beauty parlour in Delhi", "beauty_parlour"),
        ("sports coaching centre in Kolkata", "sports_coaching"),
        ("open a cricket academy in Chennai", "sports_coaching"),
        ("games parlour in Pune", "games_parlour"),
        ("gaming zone in Hyderabad", "games_parlour"),
        ("snooker club in Bengaluru", "games_parlour"),
        ("ice cream parlour in Pune", "ice_cream_parlour"),
        ("coaching centre for NEET in Delhi", "coaching_centre"),
        ("गेम पार्लर खोलना है मुंबई में", "games_parlour"),
    ],
)
def test_spa_parlour_sports_coaching_and_games(goal, activity):
    assert parse_goal_rules(goal).activity == activity
