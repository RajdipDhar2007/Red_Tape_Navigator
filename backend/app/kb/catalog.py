"""Curated seed catalogue: licences, activity profiles, cities.

IMPORTANT: this is a *seed* pack with source URLs, not a live copy of the law. Every claim derived from it is
stored with confidence < 1 and `seed=True`; fees and timelines are indicative and flagged for verification
until a live refresh confirms the source page. See docs/ASSUMPTIONS.md.
"""

# licence id -> metadata. `form` is a template id in app/forms/templates (None = complete on the portal).
LICENCES: dict[str, dict] = {
    "udyam": {
        "name": "Udyam (MSME) Registration",
        "authority": "Ministry of MSME, Government of India",
        "url": "https://udyamregistration.gov.in/",
        "form": "udyam_details",
        "depends_on": [],
        "fee": "Free of charge",
        "fee_conf": 0.85,
        "timeline": "Usually instant to a few days after Aadhaar OTP verification",
        "timeline_conf": 0.75,
        "documents": ["Aadhaar of proprietor / authorised signatory", "PAN (and GSTIN if available)", "Bank account details"],
        "why": "Free MSME identity; used by banks and for scheme eligibility.",
        "portal_login": True,
    },
    "fssai": {
        "name": "FSSAI Food Business Registration / Licence",
        "authority": "Food Safety and Standards Authority of India (FoSCoS)",
        "url": "https://foscos.fssai.gov.in/",
        "form": "fssai_form_a",
        "depends_on": ["udyam"],
        "fee": "FSSAI revised its fee slabs and licence validity in 2026; the fee is calculated on FoSCoS for your business type, so confirm the amount there before paying",
        "fee_conf": 0.35,
        "timeline": "Registration: about 7 days; State licence: about 30-60 days incl. inspection",
        "timeline_conf": 0.65,
        "documents": ["Photo ID", "Passport photo", "Proof of premises (rent agreement / ownership)", "List of food products", "Food safety management plan (licence tier)"],
        "why": "Mandatory for every food business operator in India.",
        "portal_login": True,
    },
    "trade_licence": {
        "name": "Municipal Trade Licence",
        "authority": None,  # per city
        "url": None,
        "form": "trade_licence",
        "depends_on": ["fssai"],
        "fee": "Fee varies by trade category and area; confirm with the municipal authority",
        "fee_conf": 0.5,
        "timeline": "Varies; typically 2-6 weeks including inspection",
        "timeline_conf": 0.5,
        "documents": ["Proof of premises ownership / rent agreement", "Landlord NOC (if rented)", "Property tax receipt", "ID and address proof", "Passport photo"],
        "why": "Municipal permission to carry on a trade or business from the premises.",
        "portal_login": True,
    },
    "fire_noc": {
        "name": "Fire Safety NOC",
        "authority": None,
        "url": None,
        "form": None,
        "depends_on": ["trade_licence"],
        "fee": "Fee depends on premises size and risk category; confirm with the fire service",
        "fee_conf": 0.45,
        "timeline": "Varies; inspection required",
        "timeline_conf": 0.45,
        "documents": ["Building plan / layout", "Fire extinguisher installation proof", "Trade licence copy", "Electrical safety certificate"],
        "why": "Required for food and public-facing premises with cooking equipment.",
        "portal_login": True,
    },
    "shops_est": {
        "name": "Shops and Establishments Registration",
        "authority": None,
        "url": None,
        "form": None,
        "depends_on": ["trade_licence"],
        "fee": "Fee depends on number of employees; confirm with the labour department",
        "fee_conf": 0.5,
        "timeline": "Varies; often a few working days online",
        "timeline_conf": 0.5,
        "documents": ["Trade licence copy", "ID and address proof", "Employee count declaration"],
        "why": "State labour-law registration for commercial establishments.",
        "portal_login": True,
    },
    "gst": {
        "name": "GST Registration",
        "authority": "GST Council / Goods and Services Tax Network (GSTN)",
        "url": "https://www.gst.gov.in/",
        "form": None,
        "depends_on": ["udyam"],
        "fee": "Free of charge",
        "fee_conf": 0.85,
        "timeline": "Typically 3-7 working days after application",
        "timeline_conf": 0.7,
        "documents": ["PAN", "Aadhaar", "Proof of business premises", "Bank account proof", "Passport photo"],
        "why": "Needed above the turnover threshold or for inter-state supply / e-commerce. The CGST Act (s.22) sets Rs 20 lakh (Rs 10 lakh in special category states); suppliers of goods only can have Rs 40 lakh where the state has opted in, and a few states (a CBIC 2019 update listed Telangana) kept Rs 20 lakh. Confirm the current limit for your state on the GST portal.",
        "portal_login": True,
    },
    "pollution_consent": {
        "name": "Pollution Control Board Consent (CTE/CTO)",
        "authority": "Central / State Pollution Control Board",
        "url": "https://cpcb.nic.in/",
        "form": None,
        "depends_on": ["udyam", "trade_licence"],
        "fee": "Fee depends on investment and category; confirm with the State Pollution Control Board",
        "fee_conf": 0.45,
        "timeline": "Varies by category (white/green/orange/red)",
        "timeline_conf": 0.45,
        "documents": ["Udyam certificate", "Layout plan", "Process description", "Trade licence copy"],
        "why": "Needed for manufacturing units depending on pollution category.",
        "portal_login": True,
    },
}

# activity -> licences needed (order is resolved by dependencies)
ACTIVITIES: dict[str, dict] = {
    "bakery": {"label": "Bakery", "licences": ["udyam", "fssai", "trade_licence", "fire_noc", "shops_est", "gst"], "food": True},
    "restaurant": {"label": "Restaurant", "licences": ["udyam", "fssai", "trade_licence", "fire_noc", "shops_est", "gst"], "food": True},
    "cafe": {"label": "Cafe", "licences": ["udyam", "fssai", "trade_licence", "fire_noc", "shops_est", "gst"], "food": True},
    "tea_stall": {"label": "Tea stall", "licences": ["udyam", "fssai", "trade_licence"], "food": True},
    "cloud_kitchen": {"label": "Cloud kitchen", "licences": ["udyam", "fssai", "trade_licence", "fire_noc", "gst"], "food": True},
    "sweet_shop": {"label": "Sweet shop", "licences": ["udyam", "fssai", "trade_licence", "fire_noc", "shops_est", "gst"], "food": True},
    "home_food": {"label": "Home-based food business", "licences": ["udyam", "fssai", "gst"], "food": True},
    "grocery_store": {"label": "Grocery / kirana store", "licences": ["udyam", "fssai", "trade_licence", "shops_est", "gst"], "food": True},
    "tailoring": {"label": "Tailoring shop", "licences": ["udyam", "trade_licence", "shops_est", "gst"], "food": False},
    "beauty_parlour": {"label": "Beauty parlour / salon", "licences": ["udyam", "trade_licence", "shops_est", "gst"], "food": False},
    "small_manufacturing": {"label": "Small manufacturing unit", "licences": ["udyam", "trade_licence", "pollution_consent", "gst", "shops_est"], "food": False},
    "retail_shop": {"label": "Retail shop", "licences": ["udyam", "trade_licence", "shops_est", "gst"], "food": False},
    "juice_shop": {"label": "Juice / snack counter", "licences": ["udyam", "fssai", "trade_licence"], "food": True},
    "catering": {"label": "Catering service", "licences": ["udyam", "fssai", "trade_licence", "gst"], "food": True},
    "dairy_booth": {"label": "Dairy / milk booth", "licences": ["udyam", "fssai", "trade_licence"], "food": True},
    "repair_shop": {"label": "Repair / service shop", "licences": ["udyam", "trade_licence", "shops_est", "gst"], "food": False},
    "fitness_centre": {"label": "Gym / fitness centre", "licences": ["udyam", "trade_licence", "shops_est", "gst"], "food": False},
    "coaching_centre": {"label": "Coaching / tuition centre", "licences": ["udyam", "trade_licence", "shops_est", "gst"], "food": False},
    "online_seller": {"label": "Online seller / e-commerce", "licences": ["udyam", "gst"], "food": False},
    "handicrafts": {"label": "Handicrafts / home-made goods", "licences": ["udyam", "gst"], "food": False},
    # Fallback for businesses outside the rules pack: the licences almost every shop-type business needs.
    # Activity-specific licences (e.g. drug, liquor, transport) are NOT covered; an officer reviews each such session.
    "general_business": {"label": "Other business (baseline checklist)", "licences": ["udyam", "trade_licence", "shops_est", "gst"], "food": False, "general": True},
}

# keyword synonyms (English, Bengali, Hindi) -> activity
ACTIVITY_KEYWORDS: dict[str, list[str]] = {
    "bakery": ["bakery", "baker", "bake", "cake shop", "বেকারি", "बेकरी"],
    "restaurant": ["restaurant", "dhaba", "eatery", "রেস্তোরাঁ", "রেস্টুরেন্ট", "रेस्टोरेंट", "रेस्तरां", "ढाबा"],
    "cafe": ["cafe", "café", "coffee shop", "কাফে", "कैफे"],
    "tea_stall": ["tea stall", "tea shop", "chai", "চায়ের দোকান", "चाय की दुकान", "चाय"],
    "cloud_kitchen": ["cloud kitchen", "ghost kitchen", "delivery kitchen"],
    "sweet_shop": ["sweet shop", "mithai", "sweets", "মিষ্টির দোকান", "मिठाई"],
    "home_food": ["home kitchen", "home-based food", "tiffin", "home food", "homemade food", "টিফিন", "टिफिन"],
    "grocery_store": ["grocery", "kirana", "general store", "provision store", "মুদির দোকান", "किराना"],
    "tailoring": ["tailor", "tailoring", "boutique", "দর্জি", "दर्जी", "सिलाई"],
    "beauty_parlour": ["beauty parlour", "beauty parlor", "salon", "parlour", "পার্লার", "ब्यूटी पार्लर", "सैलून"],
    "small_manufacturing": ["manufacturing", "factory", "small unit", "workshop", "কারখানা", "फैक्ट्री", "कारखाना"],
    "retail_shop": ["retail", "shop", "store", "showroom", "clothing", "garment", "stationery", "electronics", "mobile shop", "দোকান", "दुकान"],
    "juice_shop": ["juice", "snack", "fast food", "street food", "জুস", "जूस"],
    "catering": ["catering", "caterer", "ক্যাটারিং", "कैटरिंग"],
    "dairy_booth": ["dairy", "milk booth", "milk shop", "দুধ", "डेयरी", "दूध"],
    "repair_shop": ["repair", "garage", "mechanic", "service centre", "service center", "মেরামত", "मरम्मत"],
    "fitness_centre": ["gym", "fitness", "yoga", "জিম", "जिम"],
    "coaching_centre": ["coaching", "tuition", "training centre", "training center", "কোচিং", "कोचिंग", "ट्यूशन"],
    "online_seller": ["online store", "online seller", "online business", "e-commerce", "ecommerce", "amazon seller", "অনলাইন", "ऑनलाइन"],
    "handicrafts": ["handicraft", "handmade", "homemade goods", "crafts", "হস্তশিল্প", "हस्तशिल्प"],
}

CITIES: dict[str, dict] = {
    "kolkata": {
        "label": "Kolkata", "state": "West Bengal", "aliases": ["kolkata", "calcutta", "কলকাতা", "कोलकाता"],
        "authority": "Kolkata Municipal Corporation (KMC)", "trade_url": "https://www.kmcgov.in/KMCPortal/jsp/KMCTradeLicenseHome.jsp",
        "fire_authority": "West Bengal Fire & Emergency Services", "fire_url": "https://wbfireservices.gov.in/",
        "labour_authority": "West Bengal Labour Department", "labour_url": "https://lc.wb.gov.in/",
    },
    "mumbai": {
        "label": "Mumbai", "state": "Maharashtra", "aliases": ["mumbai", "bombay", "মুম্বই", "मुंबई"],
        "authority": "Brihanmumbai Municipal Corporation (MCGM)", "trade_url": "https://portal.mcgm.gov.in/",
        "fire_authority": "Maharashtra Fire Services", "fire_url": "https://www.maharashtra.gov.in/",
        "labour_authority": "Maharashtra Labour Department (Mahakamgar)", "labour_url": "https://mahakamgar.maharashtra.gov.in/lc-registration-of-shops-and-establishments.htm",
    },
    "delhi": {
        "label": "Delhi", "state": "Delhi", "aliases": ["delhi", "new delhi", "দিল্লি", "दिल्ली"],
        "authority": "Municipal Corporation of Delhi (MCD)", "trade_url": "https://mcdonline.nic.in/",
        "fire_authority": "Delhi Fire Service", "fire_url": "https://delhi.gov.in/",
        "labour_authority": "Delhi Labour Department", "labour_url": "https://labour.delhi.gov.in/hi/node/2932",
    },
    "bengaluru": {
        "label": "Bengaluru", "state": "Karnataka", "aliases": ["bengaluru", "bangalore", "বেঙ্গালুরু", "बेंगलुरु", "बैंगलोर"],
        "authority": "Greater Bengaluru Authority / BBMP (Online Trade License System)", "trade_url": "https://site.bbmp.gov.in/tradelicenseneworrenewal.html",
        "fire_authority": "Karnataka State Fire & Emergency Services", "fire_url": "https://www.karnataka.gov.in/",
        "labour_authority": "Karnataka Labour Department (eKarmika)", "labour_url": "https://www.ekarmika.karnataka.gov.in/ekarmika/static/home.aspx",
    },
    "chennai": {
        "label": "Chennai", "state": "Tamil Nadu", "aliases": ["chennai", "madras", "চেন্নাই", "चेन्नई"],
        "authority": "Greater Chennai Corporation", "trade_url": "https://chennaicorporation.gov.in/gcc/department/revenue/",
        "fire_authority": "Tamil Nadu Fire and Rescue Services", "fire_url": "https://www.tn.gov.in/",
        "labour_authority": "Tamil Nadu Labour Department", "labour_url": "https://labour.tn.gov.in/services/shop-establishments/registration",
    },
    "hyderabad": {
        "label": "Hyderabad", "state": "Telangana", "aliases": ["hyderabad", "হায়দরাবাদ", "हैदराबाद"],
        "authority": "Greater Hyderabad Municipal Corporation (GHMC)", "trade_url": "https://www.ghmc.gov.in/Trade.aspx",
        "fire_authority": "Telangana State Disaster Response & Fire Services", "fire_url": "https://www.telangana.gov.in/",
        "labour_authority": "Telangana Labour Department", "labour_url": "https://labour.telangana.gov.in/",
    },
    "pune": {
        "label": "Pune", "state": "Maharashtra", "aliases": ["pune", "poona", "পুনে", "पुणे", "पुने"],
        "authority": "Pune Municipal Corporation (PMC)", "trade_url": "https://pmc.gov.in/",
        "fire_authority": "Maharashtra Fire Services", "fire_url": "https://www.maharashtra.gov.in/",
        "labour_authority": "Maharashtra Labour Department (Mahakamgar)", "labour_url": "https://mahakamgar.maharashtra.gov.in/lc-registration-of-shops-and-establishments.htm",
    },
    "ahmedabad": {
        "label": "Ahmedabad", "state": "Gujarat", "aliases": ["ahmedabad", "আহমেদাবাদ", "अहमदाबाद"],
        "authority": "Ahmedabad Municipal Corporation (AMC)", "trade_url": "https://ahmedabadcity.gov.in/",
        "fire_authority": "Gujarat Fire Services", "fire_url": "https://www.gujarat.gov.in/",
        "labour_authority": "Ahmedabad Municipal Corporation (Shops & Establishment department)", "labour_url": "https://ahmedabadcity.gov.in/StaticPage/shops_establishment",
    },
}

STATES = sorted({c["state"] for c in CITIES.values()})
STATE_ALIASES = {
    "west bengal": "West Bengal", "বাংলা": "West Bengal", "পশ্চিমবঙ্গ": "West Bengal", "पश्चिम बंगाल": "West Bengal",
    "maharashtra": "Maharashtra", "महाराष्ट्र": "Maharashtra",
    "karnataka": "Karnataka", "कर्नाटक": "Karnataka",
    "tamil nadu": "Tamil Nadu", "तमिलनाडु": "Tamil Nadu",
    "telangana": "Telangana", "तेलंगाना": "Telangana",
    "gujarat": "Gujarat", "गुजरात": "Gujarat",
    "delhi": "Delhi",
}

REQUIRED_OVERRIDES = {
    # which per-city source feeds which licence
    "trade_licence": ("authority", "trade_url"),
    "fire_noc": ("fire_authority", "fire_url"),
    "shops_est": ("labour_authority", "labour_url"),
}
