"""Business types beyond the original pack. Pure data, merged into ``catalog.ACTIVITIES`` / ``ACTIVITY_KEYWORDS``.

Each type reuses a licence set whose rules are already in the pack (the profiles below) or one of the sourced licences in
``sourced_licences.py``. No new legal claim is made here. A type whose business is known to need extra permits that are NOT in
the pack carries ``coverage="specific"``: the app then says so and asks an officer to confirm which apply.

Keywords are matched as lower-case substrings and the LONGEST match wins, so use specific phrases ("gift shop", never "gift").
Words are English; Hindi and Bengali keywords exist only for the original types. With an Anthropic key the language model
can map other phrasings onto these types (validated against this list); without one, unknown phrasings get the baseline checklist.
"""

# ---- licence-set profiles (all licences below already exist in catalog.LICENCES) ----
RETAIL = ["udyam", "trade_licence", "shops_est", "gst"]
FOOD_RETAIL = ["udyam", "fssai", "trade_licence", "shops_est", "gst"]
FOOD_SERVICE = ["udyam", "fssai", "trade_licence", "fire_noc", "shops_est", "gst"]
STREET_FOOD = ["udyam", "fssai", "trade_licence"]
OFFICE = ["udyam", "shops_est", "gst"]
MANUFACTURING = ["udyam", "trade_licence", "pollution_consent", "gst", "shops_est"]
FOOD_MANUFACTURING = ["udyam", "fssai", "trade_licence", "pollution_consent", "gst", "shops_est"]
WAREHOUSE = ["udyam", "trade_licence", "fire_noc", "gst", "shops_est"]
ONLINE = ["udyam", "gst"]

SPECIFIC = "specific"  # extra permits exist that are not in the pack

# (id, label, licences, keywords, coverage)
_TYPES: list[tuple[str, str, list[str], list[str], str | None]] = [
    # ---------------- sourced-licence types (state-specific or national official sources) ----------------
    ("liquor_shop", "Liquor / wine shop", ["udyam", "liquor_licence", "fire_noc", "trade_licence", "shops_est", "gst"],
     ["liquor shop", "liquor store", "wine shop", "wine store", "beer shop", "beer store", "alcohol shop", "liquor vend", "wine merchant",
      "वाइन शॉप", "शराब की दुकान", "মদের দোকান", "ওয়াইন শপ"], None),
    ("pharmacy", "Pharmacy / medical store", ["udyam", "drug_licence", "trade_licence", "shops_est", "gst"],
     ["pharmacy", "chemist", "medical store", "medical shop", "medicine shop", "drug store", "medical hall", "मेडिकल स्टोर", "दवा की दुकान",
      "ফার্মেসি", "ওষুধের দোকান"], None),
    ("clinic", "Clinic / dispensary / diagnostic lab", ["clinical_registration", "bmw_authorisation"],
     ["clinic", "dispensary", "polyclinic", "doctor's chamber", "dental clinic", "eye clinic", "homeopathy clinic", "ayurveda clinic",
      "physiotherapy", "diagnostic", "pathology lab", "path lab", "scan centre", "x-ray centre", "क्लिनिक", "ক্লিনিক"], SPECIFIC),
    ("hospital", "Hospital / nursing home", ["clinical_registration", "bmw_authorisation", "fire_noc"],
     ["hospital", "nursing home", "maternity home", "hospice", "अस्पताल", "হাসপাতাল", "নার্সিং হোম"], SPECIFIC),
    ("school", "School", ["school_recognition"],
     ["school", "primary school", "high school", "kindergarten", "preschool", "स्कूल", "विद्यालय", "স্কুল", "বিদ্যালয়"], SPECIFIC),
    ("college", "College / university / institute", ["college_approval"],
     ["college", "university", "polytechnic", "engineering college", "degree college", "industrial training institute", "कॉलेज",
      "महाविद्यालय", "কলেজ"], SPECIFIC),
    ("pet_shop", "Pet shop", ["udyam", "pet_shop_registration", "trade_licence", "shops_est", "gst"],
     ["pet shop", "pet store", "aquarium shop", "dog shop", "bird shop", "pet supplies", "पेट शॉप"], None),

    # ---------------- retail (profile RETAIL) ----------------
    ("gift_shop", "Gift / novelty shop", RETAIL, ["gift shop", "gift store", "novelty shop", "party supplies"], None),
    ("toy_shop", "Toy shop", RETAIL, ["toy shop", "toy store", "toys shop"], None),
    ("book_store", "Book shop", RETAIL, ["book shop", "book store", "bookstore", "bookshop"], None),
    ("footwear_shop", "Footwear shop", RETAIL, ["footwear shop", "shoe shop", "shoe store", "chappal shop"], None),
    ("clothing_store", "Clothing / garment shop", RETAIL, ["cloth shop", "clothes shop", "garment shop", "readymade garments", "clothing store"], None),
    ("saree_shop", "Saree shop", RETAIL, ["saree shop", "saree store", "sari shop"], None),
    ("textile_shop", "Textile / fabric shop", RETAIL, ["textile shop", "fabric shop", "cloth merchant"], None),
    ("kids_wear", "Kids / baby wear shop", RETAIL, ["kids wear", "baby shop", "children's wear", "baby products"], None),
    ("mens_wear", "Men's wear shop", RETAIL, ["menswear", "men's wear", "gents wear"], None),
    ("ladies_wear", "Ladies wear shop", RETAIL, ["ladies wear", "women's wear", "ladies garment"], None),
    ("furniture_shop", "Furniture shop", RETAIL, ["furniture shop", "furniture showroom", "furniture store"], None),
    ("hardware_shop", "Hardware / building material shop", RETAIL, ["hardware shop", "hardware store", "building material", "sanitary ware"], None),
    ("electrical_shop", "Electrical / lighting shop", RETAIL, ["electrical shop", "electricals", "lighting shop"], None),
    ("electronics_shop", "Electronics / appliance shop", RETAIL, ["electronics shop", "electronics store", "tv showroom", "home appliances"], None),
    ("computer_shop", "Computer / laptop shop", RETAIL, ["computer shop", "laptop shop", "computer store"], None),
    ("mobile_store", "Mobile phone store", RETAIL, ["mobile phone shop", "mobile store", "mobile recharge", "sim card dealer"], None),
    ("cosmetics_shop", "Cosmetics / perfume shop", RETAIL, ["cosmetics shop", "beauty products shop", "perfume shop"], None),
    ("optical_shop", "Optical / eyewear shop", RETAIL, ["optical shop", "optician", "spectacle shop", "eyewear"], SPECIFIC),
    ("watch_shop", "Watch shop", RETAIL, ["watch shop", "watch showroom"], None),
    ("bag_shop", "Bag / luggage shop", RETAIL, ["bag shop", "luggage shop", "handbag shop"], None),
    ("sports_shop", "Sports goods shop", RETAIL, ["sports shop", "sports goods", "sporting goods"], None),
    ("music_shop", "Musical instruments shop", RETAIL, ["musical instrument", "music store"], None),
    ("florist", "Florist / flower shop", RETAIL, ["flower shop", "florist", "flower stall"], None),
    ("plant_nursery", "Plant nursery (retail)", RETAIL, ["plant nursery", "garden nursery", "nursery plants"], None),
    ("handloom_shop", "Handloom / khadi shop", RETAIL, ["handloom shop", "khadi store", "khadi shop"], None),
    ("home_furnishing", "Home furnishing / curtains / mattress shop", RETAIL, ["curtain shop", "furnishing shop", "home furnishing", "mattress shop"], None),
    ("kitchenware_shop", "Utensil / kitchenware shop", RETAIL, ["utensil shop", "kitchenware", "crockery shop", "steel utensils"], None),
    ("tile_shop", "Tiles / marble / granite shop", RETAIL, ["tile shop", "marble shop", "granite shop"], None),
    ("plywood_shop", "Plywood / glass / timber shop", RETAIL, ["plywood shop", "glass shop", "timber shop"], None),
    ("auto_parts", "Auto parts / tyre / battery shop", RETAIL, ["auto parts", "spare parts shop", "tyre shop", "tire shop", "battery shop"], None),
    ("cycle_shop", "Cycle shop", RETAIL, ["cycle shop", "bicycle shop"], None),
    ("puja_store", "Puja / religious items shop", RETAIL, ["puja shop", "pooja store", "religious items"], None),
    ("frame_shop", "Photo frame / framing shop", RETAIL, ["photo frame shop", "framing shop"], None),
    ("wholesale_trader", "Wholesale / trading business", RETAIL,
     ["wholesale shop", "wholesaler", "wholesale trader", "trading company", "distributor", "distribution agency"], SPECIFIC),
    ("vehicle_dealer", "Vehicle showroom / dealer", RETAIL,
     ["bike showroom", "two wheeler showroom", "motorcycle showroom", "scooter showroom", "car showroom", "car dealer", "used car"], SPECIFIC),
    ("silver_jewellery", "Silver jewellery / articles shop", RETAIL, ["silver jewellery", "silver ornaments", "silver articles"], SPECIFIC),
    ("variety_store", "Variety / general merchandise store", RETAIL, ["general merchandise", "variety store", "dollar store", "fancy store"], None),

    # ---------------- food retail / food service ----------------
    ("fruit_vegetable", "Fruit / vegetable shop", FOOD_RETAIL, ["fruit shop", "vegetable shop", "fruit and vegetable", "vegetable vendor"], SPECIFIC),
    ("meat_shop", "Meat / chicken / mutton shop", FOOD_RETAIL, ["meat shop", "chicken shop", "mutton shop", "butcher", "poultry shop"], SPECIFIC),
    ("fish_shop", "Fish / seafood shop", FOOD_RETAIL, ["fish shop", "fish market", "seafood shop"], SPECIFIC),
    ("egg_shop", "Egg shop", FOOD_RETAIL, ["egg shop"], None),
    ("ice_cream_parlour", "Ice cream parlour", FOOD_RETAIL, ["ice cream parlour", "ice cream parlor", "ice cream shop", "kulfi"], None),
    ("dry_fruit_shop", "Dry fruits / spices shop", FOOD_RETAIL, ["dry fruit shop", "dry fruits", "spice shop", "masala shop"], None),
    ("packaged_food", "Packaged food / snacks shop", FOOD_RETAIL, ["packaged food", "snack shop", "namkeen shop", "chips shop", "chocolate shop"], None),
    ("beverage_shop", "Cold drink / soda / lassi shop", FOOD_RETAIL, ["soda shop", "cold drink shop", "soft drink shop", "lassi shop", "sugarcane juice"], None),
    ("milk_products", "Milk / paneer / curd shop", FOOD_RETAIL, ["paneer shop", "curd shop", "milk products"], None),
    ("organic_store", "Organic / health food store", FOOD_RETAIL, ["organic store", "health food store", "nutrition store"], None),
    ("street_food", "Street food / food stall / food truck", STREET_FOOD, ["food truck", "pani puri", "street food stall", "chaat stall", "food stall"], None),
    ("canteen", "Canteen / mess / food court", FOOD_SERVICE, ["canteen", "mess service", "food court"], None),
    ("banquet_hall", "Banquet / function hall", FOOD_SERVICE, ["banquet hall", "marriage hall", "function hall", "wedding hall"], SPECIFIC),

    # ---------------- services (offices / service shops) ----------------
    ("barber_shop", "Barber / hair salon", RETAIL, ["barber shop", "hair salon", "mens salon", "gents salon"], None),
    ("spa_centre", "Spa / massage centre", RETAIL, ["massage centre", "massage center", "day spa", "wellness spa", "spa centre", "spa center", "body spa", "thai spa", "ayurvedic spa", "unisex spa", "spa and massage", "spa and salon", "spa parlour", "spa studio"], SPECIFIC),
    ("tattoo_studio", "Tattoo studio", RETAIL, ["tattoo studio", "tattoo shop"], None),
    ("sports_coaching", "Sports coaching academy / training centre", RETAIL,
     ["sports coaching", "sports academy", "cricket coaching", "cricket academy", "football coaching", "football academy", "badminton coaching",
      "badminton academy", "tennis coaching", "tennis academy", "chess coaching", "chess academy", "skating coaching", "archery academy",
      "sports training centre", "sports training center", "sports club"], SPECIFIC),
    ("games_parlour", "Games / gaming parlour / snooker / bowling", RETAIL,
     ["games parlour", "game parlour", "games parlor", "game parlor", "gaming parlour", "gaming zone", "gaming cafe", "gaming lounge", "video game parlour",
      "video game parlor", "game zone", "arcade", "snooker parlour", "snooker club", "pool parlour", "bowling alley", "indoor games", "esports centre",
      "e-sports centre", "vr gaming"], SPECIFIC),
    ("printing_shop", "Printing shop", RETAIL, ["printing shop", "flex printing", "digital printing", "screen printing", "offset printing"], None),
    ("courier_service", "Courier / parcel service", RETAIL, ["courier service", "courier agency", "parcel service"], None),
    ("travel_agency", "Travel agency / tour operator", RETAIL, ["travel agency", "tour operator", "tours and travels", "ticket booking"], SPECIFIC),
    ("event_management", "Event management / decorators / tent house", RETAIL,
     ["event management", "wedding planner", "event planner", "decorator", "tent house", "sound system rental", "dj service"], None),
    ("it_services", "IT / software / digital services", OFFICE,
     ["software company", "web design", "web development", "app development", "it services", "digital marketing", "graphic design", "advertising agency"], None),
    ("consulting", "Consulting / agency services", OFFICE, ["consulting firm", "consultancy", "management consultant", "recruitment agency", "placement agency"], None),
    ("accounting_firm", "Accounting / tax consultancy", OFFICE, ["tax consultant", "accounting firm", "bookkeeping", "gst consultant"], SPECIFIC),
    ("contractor", "Contractor / interior / construction services", OFFICE,
     ["civil contractor", "construction company", "interior designer", "builder", "renovation work"], SPECIFIC),
    ("solar_installer", "Solar installation / electrical contractor", OFFICE, ["solar panel", "solar installation", "electrical contractor"], SPECIFIC),
    ("hobby_classes", "Dance / music / art / sports classes", RETAIL, ["dance class", "music class", "art class", "drawing class", "karate class", "swimming class"], None),
    ("skill_training", "Computer / vocational training institute", RETAIL,
     ["computer training", "typing institute", "vocational training", "skill training", "spoken english"], SPECIFIC),
    ("daycare", "Play school / day care / creche", RETAIL, ["play school", "playschool", "day care", "daycare", "creche"], SPECIFIC),
    ("library_reading", "Library / reading room / study centre", RETAIL, ["reading room", "study centre", "study center", "library"], None),
    ("car_wash_service", "Car wash / vehicle service", RETAIL, ["car wash", "bike service", "puncture repair", "car service centre"], None),
    ("appliance_repair", "AC / appliance / computer repair", RETAIL, ["ac repair", "refrigerator repair", "computer repair", "washing machine repair", "mobile repair"], None),
    ("co_working", "Co-working space / office rental", OFFICE, ["co-working", "coworking", "office space rental"], None),
    ("hostel_pg", "Hostel / PG accommodation", FOOD_SERVICE, ["hostel", "paying guest", "pg accommodation", "boarding house"], SPECIFIC),
    ("freelancer", "Freelance / content creator business", ONLINE, ["freelance", "content creator", "youtuber", "influencer", "blogger"], None),
    ("marketplace_seller", "Social / marketplace seller", ONLINE, ["instagram seller", "facebook seller", "whatsapp business", "meesho", "flipkart seller", "reselling"], None),

    # ---------------- manufacturing / processing ----------------
    ("garment_unit", "Garment manufacturing unit", MANUFACTURING,
     ["garment factory", "garment manufacturing", "stitching unit", "embroidery unit", "readymade garment unit"], SPECIFIC),
    ("food_processing", "Food processing unit", FOOD_MANUFACTURING,
     ["food processing", "snack manufacturing", "namkeen manufacturing", "pickle manufacturing", "papad making", "masala manufacturing",
      "flour mill", "chakki", "rice mill", "oil mill"], SPECIFIC),
    ("furniture_making", "Furniture / carpentry workshop", MANUFACTURING, ["carpentry", "furniture manufacturing", "woodwork", "wood workshop"], SPECIFIC),
    ("plastic_unit", "Plastic products unit", MANUFACTURING, ["plastic manufacturing", "plastic unit", "pvc pipe"], SPECIFIC),
    ("fabrication_unit", "Fabrication / engineering workshop", MANUFACTURING,
     ["fabrication unit", "welding workshop", "steel fabrication", "engineering workshop", "lathe machine"], SPECIFIC),
    ("packaging_unit", "Packaging unit", MANUFACTURING, ["packaging unit", "carton manufacturing", "paper bag making"], SPECIFIC),
    ("soap_candle_unit", "Soap / detergent / candle unit", MANUFACTURING, ["soap manufacturing", "detergent manufacturing", "candle making", "phenyl making"], SPECIFIC),
    ("printing_press", "Printing press", MANUFACTURING, ["printing press"], SPECIFIC),
    ("bakery_unit", "Bakery / biscuit manufacturing unit", FOOD_MANUFACTURING, ["biscuit factory", "biscuit manufacturing", "bakery unit", "cake manufacturing"], SPECIFIC),
    ("ice_unit", "Ice / packaged water unit", MANUFACTURING, ["ice factory", "packaged drinking water", "mineral water plant", "water bottling"], SPECIFIC),
    ("warehouse", "Warehouse / godown / cold storage", WAREHOUSE, ["warehouse", "godown", "cold storage"], SPECIFIC),
]

EXTRA_ACTIVITIES: dict[str, dict] = {}
EXTRA_KEYWORDS: dict[str, list[str]] = {}
for _id, _label, _licences, _keywords, _coverage in _TYPES:
    entry: dict = {"label": _label, "licences": list(_licences), "food": "fssai" in _licences}
    if _coverage:
        entry["coverage"] = _coverage
    EXTRA_ACTIVITIES[_id] = entry
    EXTRA_KEYWORDS[_id] = list(_keywords)


# Hindi and Bengali keywords for the types above (common spoken/written forms, lower-case matching as substrings; the longest
# match wins). Native-speaker review is pending (docs/LAUNCH_CHECKLIST.md). Types not listed here keep English words only.
_LOCAL_KEYWORDS: dict[str, list[str]] = {
    "gift_shop": ["गिफ्ट शॉप", "उपहार की दुकान", "গিফট শপ", "উপহারের দোকান"],
    "toy_shop": ["खिलौने की दुकान", "टॉय शॉप", "খেলনার দোকান"],
    "book_store": ["किताब की दुकान", "किताबों की दुकान", "बुक स्टोर", "বইয়ের দোকান", "বুক স্টোর"],
    "footwear_shop": ["जूते की दुकान", "चप्पल की दुकान", "জুতার দোকান", "চটির দোকান"],
    "clothing_store": ["कपड़े की दुकान", "कपड़ों की दुकान", "गारमेंट शॉप", "কাপড়ের দোকান", "জামাকাপড়ের দোকান"],
    "saree_shop": ["साड़ी की दुकान", "साड़ी शोरूम", "শাড়ির দোকান"],
    "textile_shop": ["कपड़ा व्यापारी", "টেক্সটাইল", "কাপড়ের ব্যবসা"],
    "furniture_shop": ["फर्नीचर की दुकान", "फर्नीचर शोरूम", "আসবাবের দোকান", "ফার্নিচারের দোকান"],
    "hardware_shop": ["हार्डवेयर की दुकान", "हार्डवेयर शॉप", "হার্ডওয়্যারের দোকান"],
    "electrical_shop": ["बिजली की दुकान", "इलेक्ट्रिकल शॉप", "ইলেকট্রিকের দোকান"],
    "electronics_shop": ["इलेक्ट्रॉनिक्स की दुकान", "इलेक्ट्रॉनिक शॉप", "ইলেকট্রনিক্সের দোকান"],
    "computer_shop": ["कंप्यूटर की दुकान", "कंप्यूटर शॉप", "কম্পিউটারের দোকান"],
    "mobile_store": ["मोबाइल की दुकान", "मोबाइल शॉप", "मोबाइल रिचार्ज", "মোবাইলের দোকান", "মোবাইল রিচার্জ"],
    "cosmetics_shop": ["कॉस्मेटिक की दुकान", "कॉस्मेटिक शॉप", "প্রসাধনীর দোকান", "কসমেটিক্সের দোকান"],
    "optical_shop": ["चश्मे की दुकान", "ऑप्टिकल शॉप", "চশমার দোকান"],
    "watch_shop": ["घड़ी की दुकान", "ঘড়ির দোকান"],
    "bag_shop": ["बैग की दुकान", "ব্যাগের দোকান"],
    "sports_shop": ["खेल का सामान", "स्पोर्ट्स शॉप", "খেলাধুলার সামগ্রীর দোকান"],
    "florist": ["फूल की दुकान", "फूलों की दुकान", "ফুলের দোকান"],
    "plant_nursery": ["पौधों की नर्सरी", "গাছের নার্সারি"],
    "kitchenware_shop": ["बर्तन की दुकान", "बर्तनों की दुकान", "বাসনের দোকান"],
    "tile_shop": ["टाइल्स की दुकान", "मार्बल की दुकान", "টাইলসের দোকান"],
    "auto_parts": ["ऑटो पार्ट्स", "टायर की दुकान", "অটো পার্টসের দোকান", "টায়ারের দোকান"],
    "cycle_shop": ["साइकिल की दुकान", "সাইকেলের দোকান"],
    "puja_store": ["पूजा की दुकान", "पूजा सामग्री", "পূজার দোকান", "পূজার সামগ্রী"],
    "wholesale_trader": ["थोक व्यापार", "थोक की दुकान", "পাইকারি ব্যবসা", "পাইকারি দোকান"],
    "vehicle_dealer": ["गाड़ी का शोरूम", "बाइक शोरूम", "कार शोरूम", "গাড়ির শোরুম", "বাইকের শোরুম"],
    "variety_store": ["जनरल स्टोर", "জেনারেল স্টোর"],
    "fruit_vegetable": ["सब्जी की दुकान", "फल की दुकान", "सब्ज़ी की दुकान", "সবজির দোকান", "ফলের দোকান"],
    "meat_shop": ["मटन की दुकान", "चिकन की दुकान", "मीट की दुकान", "মাংসের দোকান", "মুরগির দোকান"],
    "fish_shop": ["मछली की दुकान", "মাছের দোকান", "মাছের আড়ত"],
    "egg_shop": ["अंडे की दुकान", "ডিমের দোকান"],
    "ice_cream_parlour": ["आइसक्रीम पार्लर", "आइसक्रीम की दुकान", "আইসক্রিম পার্লার", "আইসক্রিমের দোকান"],
    "dry_fruit_shop": ["मेवे की दुकान", "मसाले की दुकान", "ড্রাই ফ্রুটসের দোকান", "মশলার দোকান"],
    "packaged_food": ["नमकीन की दुकान", "স্ন্যাকসের দোকান", "নোনতার দোকান"],
    "beverage_shop": ["कोल्ड ड्रिंक की दुकान", "लस्सी की दुकान", "গন্না রসের দোকান", "লাচ্ছির দোকান"],
    "milk_products": ["पनीर की दुकान", "दही की दुकान", "ডেয়ারি", "দুধের দোকান"],
    "organic_store": ["ऑर्गेनिक स्टोर", "অর্গানিক স্টোর"],
    "street_food": ["फूड ट्रक", "ठेला", "पानी पूरी", "चाट का ठेला", "ফুড ট্রাক", "ফুচকা", "চাটের দোকান"],
    "canteen": ["कैंटीन", "ক্যান্টিন"],
    "banquet_hall": ["बैंक्वेट हॉल", "मैरिज हॉल", "शादी का हॉल", "বিয়েবাড়ি", "ব্যাংকুয়েট হল", "ম্যারেজ হল"],
    "barber_shop": ["नाई की दुकान", "हेयर सैलून", "নাপিতের দোকান"],
    "spa_centre": ["स्पा सेंटर", "मसाज सेंटर", "স্পা সেন্টার", "ম্যাসাজ সেন্টার"],
    "tattoo_studio": ["टैटू स्टूडियो", "ট্যাটু স্টুডিও"],
    "sports_coaching": ["स्पोर्ट्स कोचिंग", "क्रिकेट कोचिंग", "क्रिकेट अकादमी", "खेल अकादमी", "फुटबॉल कोचिंग", "बैडमिंटन कोचिंग",
                        "স্পোর্টস কোচিং", "ক্রিকেট কোচিং", "ক্রিকেট অ্যাকাডেমি", "ফুটবল কোচিং", "ব্যাডমিন্টন কোচিং", "খেলাধুলার প্রশিক্ষণ"],
    "games_parlour": ["गेम पार्लर", "गेमिंग जोन", "वीडियो गेम पार्लर", "स्नूकर पार्लर", "बिलियर्ड्स", "गेमिंग कैफे",
                      "গেম পার্লার", "গেমিং জোন", "ভিডিও গেম পার্লার", "স্নুকার পার্লার", "গেমিং ক্যাফে"],
    "printing_shop": ["प्रिंटिंग की दुकान", "प्रिंटिंग शॉप", "ছাপাখানার দোকান", "প্রিন্টিং শপ"],
    "courier_service": ["कूरियर सेवा", "कूरियर", "কুরিয়ার সার্ভিস", "কুরিয়ার"],
    "travel_agency": ["ट्रैवल एजेंसी", "ट्रेवल एजेंसी", "ভ্রমণ সংস্থা", "ট্রাভেল এজেন্সি"],
    "event_management": ["इवेंट मैनेजमेंट", "टेंट हाउस", "ইভেন্ট ম্যানেজমেন্ট", "টেন্ট হাউস", "ডেকোরেটর"],
    "it_services": ["सॉफ्टवेयर कंपनी", "वेब डिजाइन", "ডিজিটাল মার্কেটিং", "সফটওয়্যার কোম্পানি", "ওয়েব ডিজাইন"],
    "consulting": ["कंसल्टेंसी", "कंसल्टिंग", "কনসালটেন্সি", "পরামর্শদাতা সংস্থা"],
    "accounting_firm": ["टैक्स कंसल्टेंट", "अकाउंटिंग फर्म", "ট্যাক্স কনসালট্যান্ট", "হিসাবরক্ষণ"],
    "contractor": ["ठेकेदार", "कॉन्ट्रैक्टर", "इंटीरियर डिजाइनर", "ঠিকাদার", "কন্ট্রাক্টর", "ইন্টেরিয়র ডিজাইনার"],
    "solar_installer": ["सोलर पैनल", "সোলার প্যানেল"],
    "hobby_classes": ["डांस क्लास", "म्यूजिक क्लास", "नृत्य कक्षा", "নাচের ক্লাস", "গানের ক্লাস", "আঁকার ক্লাস"],
    "skill_training": ["कंप्यूटर प्रशिक्षण", "कंप्यूटर ट्रेनिंग", "टाइपिंग संस्थान", "কম্পিউটার প্রশিক্ষণ", "কম্পিউটার ট্রেনিং"],
    "daycare": ["डे केयर", "प्ले स्कूल", "झूलाघर", "ডে কেয়ার", "প্লে স্কুল", "ক্রেস"],
    "library_reading": ["पुस्तकालय", "लाइब्रेरी", "रीडिंग रूम", "গ্রন্থাগার", "লাইব্রেরি", "রিডিং রুম"],
    "car_wash_service": ["कार वॉश", "पंचर की दुकान", "কার ওয়াশ", "পাংচারের দোকান"],
    "appliance_repair": ["एसी रिपेयर", "मोबाइल रिपेयर", "कंप्यूटर रिपेयर", "এসি মেরামত", "মোবাইল মেরামত", "কম্পিউটার মেরামত"],
    "co_working": ["को-वर्किंग", "কো-ওয়ার্কিং"],
    "hostel_pg": ["हॉस्टल", "पेइंग गेस्ट", "হোস্টেল", "পেয়িং গেস্ট", "মেস বাড়ি"],
    "freelancer": ["फ्रीलांस", "फ्रीलांसर", "ফ্রিল্যান্স", "ফ্রিল্যান্সার"],
    "marketplace_seller": ["ऑनलाइन बेचना", "ऑनलाइन सेलर", "অনলাইনে বিক্রি", "অনলাইন সেলার"],
    "garment_unit": ["कपड़े की फैक्ट्री", "गारमेंट फैक्ट्री", "কাপড়ের কারখানা", "গার্মেন্টস কারখানা"],
    "food_processing": ["फूड प्रोसेसिंग", "आटा चक्की", "चक्की", "राइस मिल", "ফুড প্রসেসিং", "আটার কল", "চালকল"],
    "furniture_making": ["बढ़ई", "फर्नीचर बनाना", "কাঠের কাজ", "আসবাব তৈরি"],
    "plastic_unit": ["प्लास्टिक फैक्ट्री", "প্লাস্টিক কারখানা"],
    "fabrication_unit": ["फैब्रिकेशन", "वेल्डिंग वर्कशॉप", "ফ্যাব্রিকেশন", "ওয়েল্ডিং ওয়ার্কশপ"],
    "packaging_unit": ["पैकेजिंग यूनिट", "প্যাকেজিং ইউনিট"],
    "soap_candle_unit": ["साबुन बनाना", "मोमबत्ती बनाना", "সাবান তৈরি", "মোমবাতি তৈরি"],
    "printing_press": ["प्रिंटिंग प्रेस", "ছাপাখানা", "প্রিন্টিং প্রেস"],
    "bakery_unit": ["बिस्किट फैक्ट्री", "बेकरी यूनिट", "বিস্কুট কারখানা"],
    "ice_unit": ["बर्फ फैक्ट्री", "पानी का प्लांट", "বরফ কারখানা", "জলের প্লান্ট"],
    "warehouse": ["गोदाम", "वेयरहाउस", "कोल्ड स्टोरेज", "গুদাম", "ওয়্যারহাউস", "কোল্ড স্টোরেজ"],
    "pet_shop": ["पेट शॉप", "कुत्ते की दुकान", "পোষা প্রাণীর দোকান", "পেট শপ"],
}
for _id, _words in _LOCAL_KEYWORDS.items():
    EXTRA_KEYWORDS[_id].extend(w for w in _words if w not in EXTRA_KEYWORDS[_id])
