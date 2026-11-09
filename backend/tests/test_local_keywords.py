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


@pytest.mark.parametrize(
    ("goal", "activity"),
    [
        ("swimming pool in Pune", "swimming_pool"),
        ("cinema hall in Pune", "cinema_theatre"),
        ("scrap dealer in Pune", "scrap_dealer"),
        ("bike rental in Pune", "vehicle_rental"),
        ("recording studio in Pune", "recording_studio"),
        ("pizza outlet in Pune", "fast_food_outlet"),
        ("dance academy in Pune", "hobby_classes"),
        ("mehndi artist in Pune", "tattoo_studio"),
    ],
)
def test_more_business_types(goal, activity):
    assert parse_goal_rules(goal).activity == activity


@pytest.mark.parametrize(
    ("goal", "activity"),
    [
        ("चांदी के गहने की दुकान पुणे में", "silver_jewellery"),
        ("দর্জি নয়, রুপোর দোকান খুলব কলকাতায়", "silver_jewellery"),
        ("बच्चों के कपड़े की दुकान दिल्ली में", "kids_wear"),
        ("প্লাইউডের দোকান কলকাতায়", "plywood_shop"),
        ("दंत चिकित्सालय खोलना है दिल्ली में", "clinic"),
        ("খাদি ভান্ডার খুলব কলকাতায়", "handloom_shop"),
        ("नर्सिंग होम खोलना है पुणे में", "hospital"),
        ("पाठशाला खोलना है पुणे में", "school"),
    ],
)
def test_local_keywords_for_remaining_types(goal, activity):
    assert parse_goal_rules(goal).activity == activity


@pytest.mark.parametrize(
    "goal",
    ["open a bakery in Surat", "सूरत में बेकरी खोलनी है", "সুরাটে বেকারি খুলতে চাই"],
)
def test_surat_is_a_known_city_in_gujarat(goal):
    p = parse_goal_rules(goal)
    assert p.city == "Surat" and p.state == "Gujarat" and p.city_known and p.activity == "bakery"
