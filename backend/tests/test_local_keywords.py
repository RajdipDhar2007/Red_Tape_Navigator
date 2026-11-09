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
