"""Curated seed catalogue: licences, activity profiles, cities.

IMPORTANT: this is a *seed* pack with source URLs, not a live copy of the law. Every claim derived from it is
stored with confidence < 1 and `seed=True`; fees and timelines are indicative and flagged for verification
until a live refresh confirms the source page. See docs/ASSUMPTIONS.md.
"""
from app.kb.business_types import EXTRA_ACTIVITIES, EXTRA_KEYWORDS
from app.kb.sourced_licences import SOURCED_LICENCES

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
        "fee": "FSSAI fee per year (official FoSCoS list updated 01.04.2026): Rs 100 registration for turnover up to Rs 1.5 crore; Rs 5,000 State licence for turnover above Rs 1.5 crore and up to Rs 50 crore; Rs 7,500 Central licence above Rs 50 crore. A few categories differ (hawkers pay Rs 0; importers, e-commerce and five-star hotels need a Central licence), so confirm the amount for your business type on FoSCoS. A March 2026 amendment provides for perpetual validity subject to risk-based inspections; check FoSCoS for how it applies to you",
        "fee_conf": 0.85,
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
        # City-specific fee text, only where an official fee table was read. Keep wording to what the source says.
        "fee_by_city": {
            "hyderabad": (
                "GHMC publishes a trade licence fee table (linked from its trade licence page) charged per sq ft by road width: "
                "Rs 3 for a single lane (20 ft), Rs 4 for a double lane (30 ft), Rs 6 for multiple lanes (wider than 30 ft). "
                "The table does not say whether this is yearly or whether other charges apply; confirm on the GHMC page before paying"
            ),
            "kolkata": (
                "KMC publishes a 2026-27 chart of Certificate of Enlistment (trade licence) fees by nature of trade; the total is the sum of section-wise charges plus a Rs 100 processing fee, and some trades add area-based Table 1 and food-item Table 2 amounts. Examples (before those add-ons): retail seller of non-food items Rs 400; retail seller of food items Rs 300; restaurant or snack bar without manufacturing, up to 150 sq ft Rs 600, 151-300 sq ft Rs 1,000, 501-1,000 sq ft Rs 2,350; sweetmeat seller (non A/C) Rs 800; garments shop up to 500 sq ft Rs 350. Confirm your exact trade and total on the KMC chart or portal"
            ),
            "delhi": (
                "MCD publishes a Health Trade Licence fee structure (office order of 28.03.2025, 15% rise from 1 April 2025, FY 2025-28) with a one-time registration charge and an annual licence fee by trade. Eating houses: up to 20 seats Rs 10,000 registration + Rs 11,500 a year; 21 to 50 seats Rs 15,000 + Rs 23,000; above 50 seats Rs 20,000 + Rs 28,750; takeaway/others Rs 15,000 + Rs 6,900; catering Rs 10,000 + Rs 11,500; dhaba Rs 15,000 + Rs 6,900; guest house with dining Rs 10,000 + Rs 11,500. Other shops use MCD's separate General Trade Licence, whose fee chart was not read. A Rs 1,000 processing fee per application is stated in MCD's citizen charter. Confirm on the MCD portal before paying"
            ),
            "mumbai": (
                "MCGM's published Schedule of Licence Fees (Section 394, Bombay Municipal Corporation Act, Schedule M; rates per year, document undated) lists by premises area: eating house or catering establishment up to 20 sq m Rs 980, 20 to 50 Rs 1,435, 50 to 100 Rs 2,355, 100 to 150 Rs 3,335, then Rs 980 for each extra 50 sq m, maximum Rs 47,320; hair dressing saloon or barber's shop up to 20 sq m Rs 475, 20 to 40 Rs 735, 40 to 75 Rs 1,435, 75 to 100 Rs 1,770, over 100 Rs 3,590. Other trades have their own scales. Confirm the current amount on the MCGM portal before paying"
            ),
        },
        "fee_by_city_conf": 0.6,
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
        "fee_by_city": {
            "mumbai": (
                "Maharashtra Fire Prevention and Life Safety Measures Act, 2006, section 11: a Fire Service fee is levied on owners of the building types listed in Schedule II, at the Schedule's rate for that type subject to a minimum fee, and section 13 adds a further annual fee. The authority can revise the rates, so the amount for your building is fixed by the fire authority's assessment. Confirm on the Maharashtra Fire Services portal"
            ),
            "pune": (
                "Maharashtra Fire Prevention and Life Safety Measures Act, 2006, section 11: a Fire Service fee is levied on owners of the building types listed in Schedule II, at the Schedule's rate for that type subject to a minimum fee, and section 13 adds a further annual fee. The authority can revise the rates, so the amount for your building is fixed by the fire authority's assessment. Confirm on the Maharashtra Fire Services portal"
            ),
        },
        "fee_by_city_conf": 0.7,
        "timeline": "Varies; inspection required",
        "timeline_conf": 0.45,
        "documents": ["Building plan / layout", "Fire extinguisher installation proof", "Trade licence copy", "Electrical safety certificate"],
        "why": "Required for many public-facing premises (restaurants, hotels, halls, hospitals, liquor outlets); the fire authority decides by building category.",
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
        "fee_by_city": {
            "kolkata": (
                "West Bengal Shops and Establishments Act, 1963 registration fee (listed on the state's common application form page): shop with no employee Rs 25, 1 to 5 employees Rs 30, 6 to 20 Rs 40, more than 20 Rs 100; other establishment with no employee Rs 25, 1 to 5 Rs 30, 6 to 20 Rs 50, more than 20 Rs 250. Confirm the current amount on the SilpaSathi or e-District portal before paying"
            ),
            "delhi": (
                "Delhi Labour Department: registration under the Delhi Shops and Establishments Act, 1954 is available online, on a real-time basis, free of cost (department time-frame page and FAQ). Confirm on the Delhi Labour Department site before filing"
            ),
            "hyderabad": (
                "Telangana Labour Department checklist page (last reviewed 06 April 2024) lists the Shops and Establishments registration and renewal fee by number of employees: none Rs 100; 1 to 5 Rs 500; 6 to 10 Rs 1,000; 11 to 20 Rs 2,000; 21 to 50 Rs 5,000; 51 to 100 Rs 10,000; 101 and above Rs 10,000 plus Rs 5,000 for each additional 50 persons. Annual payment after 1 December carries a 25% penalty and after 31 December 50%. Confirm the current amount with the labour department before paying"
            ),
            "chennai": (
                "Tamil Nadu Shops and Establishments Rules, 1948, rule 2A (G.O. Ms. No. 55, 2 July 2024): every application for registration (Form Y) is made online through the Labour Department's web portal with a fee of Rs 100, and the Inspector issues the registration certificate (Form Z) online within 24 hours. Confirm on the Labour Department portal before filing"
            ),
            "mumbai": (
                "Maharashtra Shops and Establishments (Regulation of Employment and Conditions of Service) Rules, 2018 (Government Gazette of 23 March 2018, read from the Commissioner of Labour's PDF): no registration fee is prescribed under the Act and Rules, only the electronic transaction or service charges the Government fixes for the e-services. An establishment with ten or more workers applies online in Form A and the certificate (Form B) is signed within seven working days; an establishment with fewer than ten workers files an online intimation in Form F and gets a receipt in Form G. Confirm the current service charge and any later amendment on the Mahakamgar portal"
            ),
            "pune": (
                "Maharashtra Shops and Establishments (Regulation of Employment and Conditions of Service) Rules, 2018 (Government Gazette of 23 March 2018, read from the Commissioner of Labour's PDF): no registration fee is prescribed under the Act and Rules, only the electronic transaction or service charges the Government fixes for the e-services. An establishment with ten or more workers applies online in Form A and the certificate (Form B) is signed within seven working days; an establishment with fewer than ten workers files an online intimation in Form F and gets a receipt in Form G. Confirm the current service charge and any later amendment on the Mahakamgar portal"
            ),
            "bengaluru": (
                "Karnataka Department of Labour e-Karmika portal home page lists the registration fee by number of employees: none Rs 405; 1 to 9 Rs 810; 10 to 19 Rs 5,400; 20 to 49 Rs 13,500; 50 to 99 Rs 27,000; 100 to 250 Rs 54,000; 251 to 500 Rs 67,500; 501 to 1,000 Rs 94,500; above 1,000 Rs 1,01,250. Renewal and amendment fees are paid through Khajane-II. Confirm on e-Karmika before paying"
            ),
            "ahmedabad": (
                "Gujarat Shops and Establishments Rules, 2020, rule 4 (read from the Labour Commissionerate's PDF): for an establishment employing ten or more employees the registration fee is Rs 500 for establishments, Rs 500 for shops, Rs 2,500 for residential hotels, Rs 1,000 for restaurants and eating houses and Rs 5,000 for theatres and other places of public amusement, and the inspector issues the certificate within one day (rule 5). Gujarat Act 1 of 2026 (deemed in force from 16 December 2025) raised the registration threshold in the Act from ten to twenty workers, so confirm with the labour department which applies to you. Source of these figures: col.gujarat.gov.in (Act & Rules page)"
            ),
            "surat": (
                "Gujarat Shops and Establishments Rules, 2020, rule 4 (read from the Labour Commissionerate's PDF): for an establishment employing ten or more employees the registration fee is Rs 500 for establishments, Rs 500 for shops, Rs 2,500 for residential hotels, Rs 1,000 for restaurants and eating houses and Rs 5,000 for theatres and other places of public amusement, and the inspector issues the certificate within one day (rule 5). Gujarat Act 1 of 2026 (deemed in force from 16 December 2025) raised the registration threshold in the Act from ten to twenty workers, so confirm with the labour department which applies to you. Source of these figures: col.gujarat.gov.in (Act & Rules page)"
            ),
        },
        "fee_by_city_conf": 0.8,
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
        "timeline": "CGST Rule 9: the officer should approve a complete application within 7 working days of submission; a deficiency notice (REG-03) adds time",
        "timeline_conf": 0.9,
        "documents": ["PAN", "Aadhaar", "Proof of business premises", "Bank account proof", "Passport photo"],
        "why": "Needed above the turnover threshold or for inter-state supply / e-commerce. The CGST Act (s.22) sets Rs 20 lakh (Rs 10 lakh in special category states); suppliers of goods only can have Rs 40 lakh where the state has opted in, and a few states (a CBIC 2019 update listed Telangana) kept Rs 20 lakh. Confirm the current limit for your state on the GST portal.",
        "portal_login": True,
    },
    "bis_hallmark": {
        "name": "BIS Hallmarking Registration (jewellers)",
        "authority": "Bureau of Indian Standards (BIS)",
        "url": "https://www.manakonline.in/",
        "form": None,
        "depends_on": ["udyam"],
        "fee": "BIS charges jewellers no fee for registration (per the BIS jewellers page). Hallmarking of each article is charged separately by the hallmarking centre; confirm current charges with BIS",
        "fee_conf": 0.7,
        "timeline": "BIS states the certificate of registration is granted instantly after the online application and stays valid for life; confirm on the portal",
        "timeline_conf": 0.65,
        "documents": ["Business and proprietor details as asked on the NSWS / Manakonline application (the BIS page does not list documents; confirm on the portal)"],
        "why": "Hallmarked gold jewellery must carry the BIS mark, purity in carat and fineness, and a six-digit HUID number. Jewellers apply online for BIS registration through the NSWS portal (reachable via Manakonline). Registration is required in districts where hallmarking is mandatory; confirm for your district.",
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
        "why": "Needed for manufacturing units depending on pollution category. Sectors in the White category (practically non-polluting) do not need Consent to Operate: an intimation to the State Pollution Control Board is enough (stated on the Maharashtra board's page on the CPCB classification, with CPCB directions of 2025 adding a Blue category for essential environmental services). Check your own state board's current list.",
        "portal_login": True,
    },
}

LICENCES.update(SOURCED_LICENCES)  # licences read from official documents (state-specific ones carry by_city)

# activity -> licences needed (order is resolved by dependencies)
ACTIVITIES: dict[str, dict] = {
    "bakery": {"label": "Bakery", "licences": ["udyam", "fssai", "trade_licence", "fire_noc", "shops_est", "gst"], "food": True},
    "restaurant": {"label": "Restaurant", "licences": ["udyam", "fssai", "trade_licence", "fire_noc", "shops_est", "gst"], "food": True},
    # Food service + premises + tax registrations only. Lodging-specific registrations differ by state and are NOT in the pack,
    # so `coverage` makes the UI say so and an officer is asked to confirm (see research()).
    "hotel": {"label": "Hotel / guest house / lodge", "licences": ["udyam", "fssai", "trade_licence", "fire_noc", "shops_est", "gst"], "food": True, "coverage": "lodging"},
    "cafe": {"label": "Cafe", "licences": ["udyam", "fssai", "trade_licence", "fire_noc", "shops_est", "gst"], "food": True},
    "tea_stall": {"label": "Tea stall", "licences": ["udyam", "fssai", "trade_licence"], "food": True},
    "cloud_kitchen": {"label": "Cloud kitchen", "licences": ["udyam", "fssai", "trade_licence", "fire_noc", "gst"], "food": True},
    "sweet_shop": {"label": "Sweet shop", "licences": ["udyam", "fssai", "trade_licence", "fire_noc", "shops_est", "gst"], "food": True},
    "home_food": {"label": "Home-based food business", "licences": ["udyam", "fssai", "gst"], "food": True},
    "grocery_store": {"label": "Grocery / kirana store", "licences": ["udyam", "fssai", "trade_licence", "shops_est", "gst"], "food": True},
    "jewellery": {"label": "Gold / jewellery shop", "licences": ["udyam", "bis_hallmark", "trade_licence", "shops_est", "gst"], "food": False},
    "tailoring": {"label": "Tailoring shop", "licences": ["udyam", "trade_licence", "shops_est", "gst"], "food": False},
    "beauty_parlour": {"label": "Beauty parlour / salon", "licences": ["udyam", "trade_licence", "shops_est", "gst"], "food": False},
    "small_manufacturing": {"label": "Small manufacturing unit", "licences": ["udyam", "trade_licence", "pollution_consent", "gst", "shops_est"], "food": False},
    "retail_shop": {"label": "Retail shop", "licences": ["udyam", "trade_licence", "shops_est", "gst"], "food": False},
    "juice_shop": {"label": "Juice / snack counter", "licences": ["udyam", "fssai", "trade_licence"], "food": True},
    "catering": {"label": "Catering service", "licences": ["udyam", "fssai", "trade_licence", "gst"], "food": True},
    "dairy_booth": {"label": "Dairy / milk booth", "licences": ["udyam", "fssai", "trade_licence"], "food": True},
    "repair_shop": {"label": "Repair / service shop", "licences": ["udyam", "trade_licence", "shops_est", "gst"], "food": False},
    "fitness_centre": {"label": "Gym / fitness centre", "licences": ["udyam", "trade_licence", "shops_est", "gst"], "food": False},
    "coaching_centre": {"label": "Coaching / tuition centre", "licences": ["udyam", "coaching_registration", "trade_licence", "shops_est", "gst"], "food": False},
    "online_seller": {"label": "Online seller / e-commerce", "licences": ["udyam", "gst"], "food": False},
    "handicrafts": {"label": "Handicrafts / home-made goods", "licences": ["udyam", "gst"], "food": False},
    # Fallback for businesses outside the rules pack: the licences almost every shop-type business needs.
    # Activity-specific licences (e.g. drug, liquor, transport) are NOT covered; an officer reviews each such session.
    "general_business": {"label": "Other business (baseline checklist)", "licences": ["udyam", "trade_licence", "shops_est", "gst"], "food": False, "general": True},
}

ACTIVITIES.update(EXTRA_ACTIVITIES)  # ~110 more business types (see business_types.py)

# keyword synonyms (English, Bengali, Hindi) -> activity
ACTIVITY_KEYWORDS: dict[str, list[str]] = {
    "bakery": ["bakery", "baker", "bake", "cake shop", "cakes", "cake", "pastry", "pastries", "bread shop", "bakary", "bekary", "backery", "bakry", "বেকারি", "बेकरी"],
    "restaurant": ["restaurant", "dhaba", "eatery", "resturent", "restaurent", "restarant", "resturant", "restraunt", "restorent", "resteraunt", "restuarant", "family restaurant", "রেস্তোরাঁ", "রেস্টুরেন্ট", "रेस्टोरेंट", "रेस्तरां", "ढाबा"],
    "hotel": ["hotel", "guest house", "guesthouse", "lodge", "lodging", "homestay", "home stay", "হোটেল", "গেস্ট হাউস", "लॉज", "होटल", "गेस्ट हाउस"],
    "cafe": ["cafe", "café", "cafee", "coffee shop", "coffee house", "কাফে", "कैफे"],
    "tea_stall": ["tea stall", "tea shop", "chai", "চায়ের দোকান", "चाय की दुकान", "चाय"],
    "cloud_kitchen": ["cloud kitchen", "ghost kitchen", "delivery kitchen"],
    "sweet_shop": ["sweet shop", "mithai", "sweets", "মিষ্টির দোকান", "मिठाई"],
    "home_food": ["home kitchen", "home-based food", "tiffin", "home food", "homemade food", "টিফিন", "टिफिन"],
    "grocery_store": ["grocery", "grocary", "grosery", "kirana", "general store", "provision store", "supermarket", "departmental store", "মুদির দোকান", "किराना"],
    "jewellery": ["gold shop", "gold store", "gold dealer", "gold jewel", "jewellery", "jewelry", "jeweller", "jeweler", "ornament shop", "silver shop", "সোনার দোকান", "গয়না", "জুয়েলারি", "সোনা", "सोने की दुकान", "ज्वेलरी", "गहने", "सुनार", "ज्वैलर"],
    "tailoring": ["tailor", "tailoring", "boutique", "দর্জি", "दर्जी", "सिलाई"],
    "beauty_parlour": ["beauty parlour", "beauty parlor", "salon", "saloon", "parlour", "পার্লার", "ब्यूटी पार्लर", "सैलून"],
    "small_manufacturing": ["manufacturing", "factory", "small unit", "workshop", "কারখানা", "फैक्ट्री", "कारखाना"],
    "retail_shop": ["retail", "shop", "store", "showroom", "clothing", "garment", "stationery", "electronics", "mobile shop", "gift", "toy", "footwear", "furniture", "hardware", "saree", "textile", "fabric", "cosmetic", "দোকান", "दुकान", "গিফট", "गिफ्ट", "उपहार"],
    "juice_shop": ["juice", "snack", "fast food", "street food", "জুস", "जूस"],
    "catering": ["catering", "caterer", "ক্যাটারিং", "कैटरिंग"],
    "dairy_booth": ["dairy", "milk booth", "milk shop", "দুধ", "डेयरी", "दूध"],
    "repair_shop": ["repair", "garage", "mechanic", "service centre", "service center", "xerox", "photocopy", "cyber cafe", "laundry", "dry clean", "photo studio", "মেরামত", "मरम्मत"],
    "fitness_centre": ["gym", "fitness", "yoga", "জিম", "जिम"],
    "coaching_centre": ["coaching", "tuition", "training centre", "training center", "কোচিং", "कोचिंग", "ट्यूशन"],
    "online_seller": ["online store", "online seller", "online business", "e-commerce", "ecommerce", "amazon seller", "অনলাইন", "ऑनलाइन"],
    "handicrafts": ["handicraft", "handmade", "homemade goods", "crafts", "হস্তশিল্প", "हस्तशिल्प"],
}

ACTIVITY_KEYWORDS.update(EXTRA_KEYWORDS)

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
    "surat": {
        "label": "Surat", "state": "Gujarat", "aliases": ["surat", "সুরাট", "सूरत"],
        "authority": "Surat Municipal Corporation (SMC)", "trade_url": "https://www.suratmunicipal.gov.in/",
        "fire_authority": "Gujarat Fire Services", "fire_url": "https://www.gujarat.gov.in/",
        "labour_authority": "Surat Municipal Corporation (Shops & Establishment)", "labour_url": "https://www.suratmunicipal.gov.in/",
    },
}

# Businesses whose main licence comes from a sector regulator, not from the shop/municipal route this product covers.
# Only the regulator is named (a stable fact); no fees, timelines or conditions are stated. `pattern` is a regex on lower-case
# text with word boundaries, so "blood bank" or "food bank" is not mistaken for a bank.
REGULATED_SECTORS: dict[str, dict] = {
    # mode "operated": the service is run by the authority itself, so there is no licence to obtain (default mode is "regulated").
    "postal": {"regulator": "India Post (Department of Posts)", "url": "https://www.indiapost.gov.in/", "mode": "operated",
               "pattern": r"\bpost ?offices?\b|\bindia post\b"},
    "bank": {"regulator": "the Reserve Bank of India (RBI)", "url": "https://www.rbi.org.in/",
             "pattern": r"(?<!blood )(?<!food )(?<!seed )(?<!eye )(?<!milk )\bbank(?:s|ing)?\b"},
    "nbfc": {"regulator": "the Reserve Bank of India (RBI)", "url": "https://www.rbi.org.in/",
             "pattern": r"\bnbfc\b|\bmicro ?finance\b|\bfinance compan(?:y|ies)\b|\bloan compan(?:y|ies)\b|\bgold loan\b"},
    "insurance": {"regulator": "the Insurance Regulatory and Development Authority of India (IRDAI)", "url": "https://irdai.gov.in/",
                  "pattern": r"\binsurance\b"},
    "securities": {"regulator": "the Securities and Exchange Board of India (SEBI)", "url": "https://www.sebi.gov.in/",
                   "pattern": r"\bstock ?brok\w*|\bshare brok\w*|\bbroking\b|\bmutual funds?\b|\bportfolio manage\w*|\binvestment advis\w*"},
    # mode "authorised": the state appoints/authorises the outlet; it is not opened through a licence application.
    "ration": {"regulator": "your State Food and Civil Supplies Department", "url": None, "mode": "authorised", "shop_like": True,
               "pattern": r"\bration (?:shop|store|dealer|depot)s?\b|\bfair price (?:shop|store)s?\b|\bpds (?:shop|dealer|outlet)s?\b"},
    "firecrackers": {"regulator": "the Petroleum and Explosives Safety Organisation (PESO)", "url": "https://peso.gov.in/", "shop_like": True,
                     "pattern": r"\bfire ?crackers?\b|\bfireworks?\b|\bcrackers? (?:shop|store)s?\b"},
    "agri_inputs": {"regulator": "your State Agriculture Department", "url": None, "shop_like": True,
                    "pattern": r"\bpesticides?\b|\bpest control\b|\bfertili[sz]ers?\b|\bseed (?:shop|store|dealer)s?\b|\bagro ?(?:shop|centre|center)s?\b"},
    "forex": {"regulator": "the Reserve Bank of India (RBI)", "url": "https://www.rbi.org.in/",
              "pattern": r"\bmoney chang\w*\b|\bforex\b|\bforeign exchange\b"},
    "transport": {"regulator": "your State Transport Department (vehicle permits)", "url": None,
                  "pattern": r"\btaxi\b|\bcab service\b|\bbus service\b|\btrucking\b|\btransport (?:company|business|service)\b"},
    "real_estate": {"regulator": "your State Real Estate Regulatory Authority (RERA), where agents register", "url": None,
                    "pattern": r"\breal estate (?:agent|agency|broker)s?\b|\bproperty (?:dealer|broker)s?\b|\bestate agent\b"},
    "driving_school": {"regulator": "your State Transport Department (RTO), which licenses driving schools", "url": None,
                       "pattern": r"\bdriving school\b|\bmotor driving training\b"},
    "security_agency": {"regulator": "your State Government's Home Department (licence under the Private Security Agencies (Regulation) Act, 2005)", "url": None,
                        "pattern": r"\bsecurity agenc(?:y|ies)\b|\bsecurity guard (?:service|agency)\b"},
    "professional": {"regulator": "the relevant professional council (for example the Bar Council, ICAI, the Council of Architecture or your State Veterinary Council)", "url": None,
                     "pattern": r"\blaw firm\b|\badvocate'?s? office\b|\bchartered accountant\b|\barchitect (?:firm|office)\b|\bveterinary clinic\b|\bvet clinic\b|\banimal hospital\b"},
    "telecom": {"regulator": "the Department of Telecommunications (DoT)", "url": "https://dot.gov.in/",
                "pattern": r"\binternet service provider\b|\btelecom\b"},
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
