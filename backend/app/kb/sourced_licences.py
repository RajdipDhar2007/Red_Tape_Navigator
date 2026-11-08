"""Licences added from OFFICIAL documents read on 2026-11-08 (source URLs are in each entry and in docs/RULES_VERIFICATION.md).

Pure data, merged into ``catalog.LICENCES``. Rules of this file:
  * only what an official page/document said is stated; anything not found says so ("not stated", "confirm with ...");
  * every claim built from these entries stays flagged for a reviewer (confidence < 0.9) until an officer signs it off;
  * ``by_city`` licences are state-specific: each of the 8 pilot cities has an entry written from its state's own official source,
    or says plainly that the state's page could not be read. ``restricted`` marks states where the official source shows there is
    no ordinary private route (the UI then explains this prominently instead of listing a checklist that cannot be completed).
"""

def _same(entry: dict, cities: tuple[str, ...]) -> dict[str, dict]:
    return {c: dict(entry) for c in cities}


# ---------------------------------------------------------------- liquor (state-specific)
_WB_DOCS = [
    "Passport-size photograph of the applicant (uploaded as an image)",
    "Self-attested proof of nationality: Voter ID, passport or PAN card (or a P.I.O. status certificate)",
    "Self-attested proof of date of birth: birth certificate, Madhyamik or equivalent admit card, or PAN card",
    "Self-attested highest educational qualification certificate",
    "Affidavit declaring medical fitness",
    "Affidavit that you have not been convicted by a criminal court for a non-bailable offence",
    "Income tax returns for the last 3 years",
    "Any other proof of solvency",
    "Site: Record of Rights, parcha, sale/title/conveyance/lease/tenancy deed or property tax receipt",
    "Site: NOC from the landowner or competent authority if you do not own the site",
    "Site: proof of commercial use, or the commercial-conversion application if the land is not yet converted",
    "Site: site plan prepared by an approved surveyor, with seal, signed by the applicant",
    "Site: current FSSAI food licence, if applicable",
    "Site: affidavit that the licence may be cancelled if the information given is false",
    "Site: valid fire licence",
    "Site: valid trade licence or certificate of enlistment",
]

_MH = {
    "authority": "District Collector, through the Superintendent of State Excise of your district (Maharashtra State Excise)",
    "url": "https://stateexcise.maharashtra.gov.in/1178/FL-II",
    "fee": "Application fee for the FL-II (foreign liquor vendor) licence, Form FL/A-IB: Rs 2,000 if the population is above 1 lakh, otherwise Rs 1,000. "
           "The licence fee is on the department's separate 'current licence fee' page, which was not read; confirm it with the Superintendent of State Excise",
    "fee_conf": 0.5,
    "timeline": "Not stated. The page says a police antecedent report is required and the distance rules (educational and religious institutions, State Transport depots) are checked",
    "timeline_conf": 0.3,
    "documents": [
        "Application in Form FL/A-IB",
        "Exact location of the proposed premises (mandatory)",
        "Solvency certificate (mandatory)",
        "Affidavit that no Income Tax or Sales Tax dues are pending",
        "Plans of the premises",
    ],
    "why": "Maharashtra: the department's FL-II page says 'There is ban on grant of new license'. That page was last reviewed on 23/09/2014, so confirm the current position with the "
           "Superintendent of State Excise before spending money. The FL/W-II wine-retail licence is granted only to wine manufacturers holding a BRL licence, on their own manufactory premises.",
    "restricted": True,
}

LIQUOR = {
    "name": "Liquor Retail Licence (wine shop / liquor vend)",
    "authority": "State Excise / Prohibition Department of your state",
    "url": "https://excise.wb.gov.in/",
    "form": None,
    "depends_on": [],
    "fee": "Set by each state; see the entry for your city",
    "fee_conf": 0.4,
    "timeline": "Set by each state; see the entry for your city",
    "timeline_conf": 0.3,
    "documents": ["Set by each state; see the entry for your city"],
    "why": "Selling liquor needs a licence from the state excise department, and every state has its own policy, licence classes and fees.",
    "portal_login": True,
    "by_city": {
        "kolkata": {
            "authority": "Excise Directorate, Government of West Bengal",
            "url": "https://excise.wb.gov.in/",
            "fee": "The application fee is paid online through GRIPS (the amount is not shown on the portal page). Registration and annual fees depend on the licence category and area; confirm them in the Excise Directorate's current fee notification",
            "fee_conf": 0.5,
            "timeline": "Not stated on the portal page. The page asks whether you already hold a Letter of Intent (LOI); how the LOI is obtained is not described there",
            "timeline_conf": 0.3,
            "documents": _WB_DOCS,
            "why": "West Bengal: apply on the Excise Directorate portal. You choose your police station, upload the applicant and proposed-site documents listed here and pay the application fee through GRIPS (steps as shown on the portal's application page).",
        },
        "mumbai": dict(_MH),
        "pune": dict(_MH),
        "delhi": {
            "authority": "Excise Department, Government of NCT of Delhi",
            "url": "https://excise.delhi.gov.in/excise/licences",
            "fee": "For the L-6 retail vend licence the department states Rs 2,50,000 as the licence fee, deposited by the government corporation before the licence is issued",
            "fee_conf": 0.5,
            "timeline": "Not stated on the licences page",
            "timeline_conf": 0.3,
            "documents": [
                "No applicant documents are listed for L-6; retail vends are applied for through the government corporations",
                "Premises: pucca building with a minimum floor area of 150 sq ft on a floor, in a commercial area, passing a site inspection",
                "Premises must not be within 100 metres of major educational institutions, religious places, or hospitals with fifty beds and above",
            ],
            "why": "Delhi: the department's licences page says L-6 retail vend licences are granted only to selected Delhi government undertakings (DTTDC, DSIDC, DSCSC and DCCWS), and describes no "
                   "application route for a private individual to open a retail liquor shop. Hotels, restaurants and clubs have separate licence classes (L-15 to L-18, L-28, L-29).",
            "restricted": True,
        },
        "bengaluru": {
            "authority": "State Excise Department, Karnataka",
            "url": "https://stateexcise.karnataka.gov.in/",
            "fee": "Retail liquor shops are licensed as CL-2. The department's licence-fee page has a CL-2 row with two tiers by population, but the amounts could not be read reliably from here; confirm the current fee with the department",
            "fee_conf": 0.3,
            "timeline": "Not found on the pages that could be read",
            "timeline_conf": 0.2,
            "documents": ["The document list for a CL-2 licence was not found on the department's site; ask your district excise office"],
            "why": "Karnataka: retail liquor shops are licensed as CL-2 by the State Excise Department. The department's pages could not be read securely from here, so no document list is shown; please ask your district excise office.",
        },
        "chennai": {
            "authority": "Prohibition and Excise Department, Government of Tamil Nadu",
            "url": "https://www.cpe.tn.gov.in/",
            "fee": "Not applicable to a private retail shop: under the Tamil Nadu Liquor Retail Vending (in Shops and Bars) Rules, 2003 the retail licence is held by the state marketing corporation (TASMAC)",
            "fee_conf": 0.5,
            "timeline": "Not applicable",
            "timeline_conf": 0.4,
            "documents": ["No private application route for a retail liquor shop is described in these Rules. Other licence classes have their own rules on the department's site"],
            "why": "Tamil Nadu: the Tamil Nadu Liquor Retail Vending (in Shops and Bars) Rules, 2003 grant the retail vending licence to the state marketing corporation (TASMAC). These Rules are old, "
                   "so confirm the current position with the Prohibition and Excise Department.",
            "restricted": True,
        },
        "hyderabad": {
            "authority": "Prohibition & Excise Department, Government of Telangana",
            "url": "https://excise.telangana.gov.in/",
            "fee": "For the 2023-25 licence period (1 Dec 2023 to 30 Nov 2025) the application fee was Rs 2,00,000 per shop, non-refundable (G.O.Ms.No.86, 01.08.2023). The successful applicant also paid one-sixth of the annual retail shop excise tax on the day of the lots drawing. Fees for the current period are in the latest notification, which was not found",
            "fee_conf": 0.4,
            "timeline": "Shops are allotted by drawing of lots for each licence period, after a notification; applications are accepted only in the notified window",
            "timeline_conf": 0.4,
            "documents": [
                "Application in the prescribed form (Annexure 1 to the G.O.)",
                "Three passport-size photographs of the applicant and of any authorised representative",
                "Self-certified Aadhaar and PAN cards",
                "Caste certificate where a reserved category applies (and a Local Area Scheduled Tribe certificate for shops in scheduled areas)",
                "Application fee by demand draft or challan in favour of the District Prohibition and Excise Officer",
                "Applications were submitted in person at the notified places, not by post, courier or email",
            ],
            "why": "Telangana: retail (A4) shops are allotted by lottery for each licence period. In the 2023 notification, people below 21, those convicted under the Excise Act, excise defaulters and "
                   "adjudged insolvents were barred. The notification for the current period was not found, so check the department's site.",
        },
        "ahmedabad": {
            "authority": "Prohibition and Excise Department, Government of Gujarat",
            "url": "https://prohibition-excise.gujarat.gov.in/",
            "fee": "Not applicable: no licence for an ordinary liquor shop was found",
            "fee_conf": 0.5,
            "timeline": "Not applicable",
            "timeline_conf": 0.4,
            "documents": ["Not applicable. Health permits for foreign liquor (section 40A of the Act) go to individuals who need it for their health, issued by an officer the State Government authorises"],
            "why": "Gujarat is a prohibition state. The Gujarat Prohibition Act, 1949 bars the manufacture, sale, purchase and possession of liquor unless a licence or permit allows it, and provides "
                   "for health permits (section 40A). No route to open an ordinary liquor shop was found; ask the Prohibition and Excise Department.",
            "restricted": True,
        },
    },
}

# ---------------------------------------------------------------- pharmacy (drug licence)
_DELHI_DRUG_DOCS = [
    "System-generated online fee deposit receipt(s)",
    "System-generated application in Form 19 / 19C, as applicable",
    "System-generated self-declaration of the proprietor / partners / directors",
    "Site plan and key plan of the premises",
    "Proof of constitution of the firm (proprietorship declaration; partnership deed with list of partners; LLP deed and ROC certificate; memorandum, articles, ROC certificate and board resolution for a company; trust deed; society by-laws; HUF deed)",
    "Photo ID proof of the proprietor / partner / director",
    "Affidavit of non-conviction of the proprietor / partner / director and the firm under the Drugs & Cosmetics Act, 1940",
    "Affidavit of compliance with the Delhi Master Plan (MPD-2021) for the type of premises",
    "Receipt of applicable charges (such as registration or conversion charges) issued by MCD, with documents supporting commercial use",
    "Registered Pharmacist (technical person): Aadhaar, self-declaration, qualification certificates and mark sheets, valid Delhi Pharmacy Council registration, appointment letter, bio-data in the prescribed format",
    "Premises: registered sale deed / GPA / conveyance deed (or unregistered ones with electricity bill, water bill or property tax receipt); if rented, rent receipt and rent agreement with the landlord's ownership documents",
    "Premises must be an independent shop of at least 10 sq m (15 sq m for both Form 20/21 and 20B/21B), with clear height per the National Building Code",
    "All documents are to be self-attested; no drug licence is granted in a residential plot or flat unless MPD-2021 allows it",
]

_DRUG_GENERIC_DOCS = [
    "Application in Form 19 (as used in the Delhi checklist; confirm your state's system and form)",
    "Site plan of the premises and proof of premises (ownership or rent agreement)",
    "Proof of constitution of the firm and photo ID of the proprietor / partners / directors",
    "Affidavit of non-conviction under the Drugs & Cosmetics Act, 1940",
    "Registered Pharmacist: qualification certificates, state pharmacy council registration and appointment letter",
    "Premises: an independent shop of at least 10 sq m (15 sq m if both Form 20/21 and 20B/21B are sought)",
    "This list is based on the Delhi Drugs Control Department's official checklist; your state's checklist may differ in details, so confirm it with your State Drugs Control Department",
]

_DRUG_BASE = {
    "authority": "State Drugs Control Department (State Licensing Authority under the Drugs Rules, 1945)",
    "url": "https://cdsco.gov.in/opencms/resources/UploadCDSCOWeb/2022/drug_rules/Drugs%20Rules,%201945.pdf",
    "fee": "The amount is not stated in the checklist that was read; the fee is paid online or by challan with the application. Confirm it with your State Drugs Control Department",
    "fee_conf": 0.4,
    "timeline": "Not stated in the checklist that was read",
    "timeline_conf": 0.3,
    "documents": _DRUG_GENERIC_DOCS,
    "why": "Retail sale of drugs needs a licence from the State Licensing Authority under the Drugs Rules, 1945: Form 20 (allopathic drugs outside Schedules C, C(1) and X), Form 21 (Schedule C and C(1) drugs, "
           "excluding Schedule X) and Form 20F (Schedule X). A registered pharmacist (or another competent person the Rules allow) must be in charge of the premises.",
}

DRUG = {
    "name": "Retail Drug (Pharmacy) Licence",
    "authority": _DRUG_BASE["authority"],
    "url": _DRUG_BASE["url"],
    "form": None,
    "depends_on": [],
    "fee": _DRUG_BASE["fee"],
    "fee_conf": 0.4,
    "timeline": _DRUG_BASE["timeline"],
    "timeline_conf": 0.3,
    "documents": _DRUG_GENERIC_DOCS,
    "why": _DRUG_BASE["why"],
    "portal_login": True,
    "by_city": {
        **_same(_DRUG_BASE, ("kolkata", "mumbai", "bengaluru", "chennai", "hyderabad", "pune", "ahmedabad")),
        "delhi": {
            **_DRUG_BASE,
            "authority": "Department of Drugs Control, Government of NCT of Delhi",
            "url": "https://drugs.delhi.gov.in/drugs/procedures-obtaining-licences",
            "documents": _DELHI_DRUG_DOCS,
            "why": str(_DRUG_BASE["why"]) + " Delhi's official checklist (Forms 20, 21 and 20F) is shown here.",
        },
    },
}

SOURCED_LICENCES: dict[str, dict] = {
    "liquor_licence": LIQUOR,
    "drug_licence": DRUG,
    "pet_shop_registration": {
        "name": "Pet Shop Registration (State Animal Welfare Board)",
        "authority": "State Animal Welfare Board of your state (Prevention of Cruelty to Animals (Pet Shop) Rules, 2018)",
        "url": "https://awbi.gov.in/Document/rules",
        "form": None,
        "depends_on": [],
        "fee": "Non-refundable application fee of Rs 5,000 with Form-I, and a separate application for every pet shop or premises. Renewal also costs Rs 5,000 (Pet Shop Rules, 2018)",
        "fee_conf": 0.8,
        "timeline": "The certificate is valid for five years; apply for renewal at least thirty days before it expires. The State Board has the shop inspected by an authorised inspector (a State Government veterinarian) before registering",
        "timeline_conf": 0.7,
        "documents": [
            "Application in Form-I (First Schedule of the Rules) giving all the information the form asks for",
            "Rs 5,000 non-refundable application fee",
            "A permanent structure or building with water, electricity and housing for the animals as set out in rule 6 of the Rules",
            "After registration: display the certificate in the shop and keep the shop open for inspection",
        ],
        "why": "No one may run a pet shop, retail or wholesale, without a certificate of registration from the State Animal Welfare Board. Shops already operating had to apply within sixty days of the Rules "
               "coming into force, and an unregistered shop can be sealed and its animals confiscated (Rules, 2018).",
        "portal_login": False,
    },
    "clinical_registration": {
        "name": "Clinic / Hospital / Laboratory Registration",
        "authority": "State or district health authority under your state's clinical-establishment law (the central Act applies only in the states listed by the Health Ministry)",
        "url": "https://clinicalestablishments.mohfw.gov.in/faq",
        "form": None,
        "depends_on": [],
        "fee": "Not stated in the Health Ministry's FAQ; confirm with your state health authority",
        "fee_conf": 0.3,
        "timeline": "Not stated in the Health Ministry's FAQ; confirm with your state health authority",
        "timeline_conf": 0.3,
        "documents": [
            "Documents depend on your state's law. Where the central Clinical Establishments Act, 2010 applies, registration is in two steps: provisional (self-declaration, without inquiry or inspection) and permanent (after category-wise minimum standards are notified)",
            "Confirm with your state health department or District Registering Authority which law and forms apply to you",
        ],
        "why": "The Clinical Establishments Act, 2010 covers hospitals, maternity homes, nursing homes, dispensaries, clinics, sanatoriums and laboratory/diagnostic centres, across all systems of medicine. "
               "The Health Ministry's FAQ says it is in force in Arunachal Pradesh, Sikkim, Mizoram, Himachal Pradesh and all Union Territories except Delhi, and in states that adopted it "
               "(Uttar Pradesh, Bihar, Rajasthan, Jharkhand, Uttarakhand). Elsewhere a state's own law and health authority apply, so check with your state.",
        "portal_login": False,
    },
    "bmw_authorisation": {
        "name": "Bio-Medical Waste Authorisation (State Pollution Control Board)",
        "authority": "State Pollution Control Board / Pollution Control Committee",
        "url": "https://cpcb.nic.in/rules-3/",
        "form": None,
        "depends_on": [],
        "fee": "Not stated in the sources read; confirm with your State Pollution Control Board",
        "fee_conf": 0.3,
        "timeline": "Not stated in the sources read; the authorisation carries an expiry date, so plan its renewal",
        "timeline_conf": 0.3,
        "documents": ["Application to the State Pollution Control Board as an occupier under the Bio-Medical Waste Management Rules, 2016 (the exact form and annexures are in the Rules text on the CPCB site)"],
        "why": "Under the Bio-Medical Waste Management Rules, 2016 every occupier or operator who generates or handles bio-medical waste, irrespective of quantity, must obtain authorisation from the State "
               "Pollution Control Board. The Rules cover hospitals, nursing homes, clinics and dispensaries.",
        "portal_login": True,
    },
    "school_recognition": {
        "name": "School Recognition (RTE Act) and CBSE affiliation",
        "authority": "State Education Department (recognition under the RTE Act); CBSE for CBSE affiliation",
        "url": "https://www.cbse.gov.in/cbsenew/aff_bye_laws.html",
        "form": None,
        "depends_on": [],
        "fee": "Not stated in the sources read; the state sets recognition fees and CBSE publishes its own affiliation fees",
        "fee_conf": 0.3,
        "timeline": "Not stated in the sources read",
        "timeline_conf": 0.3,
        "documents": [
            "Certificate of recognition from the State Education Department under section 18 of the Right of Children to Free and Compulsory Education Act, 2009 (application in the form your state prescribes)",
            "For CBSE affiliation (optional): apply only on CBSE's SARAS portal with the state recognition certificate and a State NOC that names the classes (CBSE affiliation bye-laws)",
        ],
        "why": "Under section 18 of the RTE Act no school, other than one owned or controlled by the government or a local authority, may be established or function without a certificate of recognition "
               "from the prescribed authority. CBSE affiliation is a separate, optional step that needs that recognition first. Building-safety, fire and land-use approvals for school buildings differ by state; an officer will confirm.",
        "portal_login": False,
    },
    "college_approval": {
        "name": "College / Technical Institution approvals",
        "authority": "Affiliating university; AICTE for technical institutions",
        "url": "https://www.aicte-india.org/bureaus/approval",
        "form": None,
        "depends_on": [],
        "fee": "AICTE sets fees and deadlines for each approval cycle; confirm the current year's notice",
        "fee_conf": 0.3,
        "timeline": "AICTE runs approval in annual cycles with set last dates; check the current cycle",
        "timeline_conf": 0.4,
        "documents": [
            "For technical institutions (diploma, degree or postgraduate programmes): register and apply for AICTE approval through the NSWS portal, following AICTE's current approval-process handbook and its list of affidavits, certificates and formats",
            "For other colleges: affiliation to a university, under that university's own affiliation rules (not read)",
        ],
        "why": "AICTE's approval process applies to new technical institutions and to added courses or intake at existing ones. Other colleges generally work under an affiliating university. "
               "The UGC position and each university's affiliation rules were not read, so an officer will confirm which apply.",
        "portal_login": True,
    },
    "coaching_registration": {
        "name": "Coaching Centre Registration (state rules)",
        "authority": "State government authority under your state's coaching-centre rules (where notified)",
        "url": "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2298513&reg=48&lang=2",
        "form": None,
        "depends_on": [],
        "fee": "State-specific; not stated in the sources read",
        "fee_conf": 0.3,
        "timeline": "State-specific; not stated in the sources read",
        "timeline_conf": 0.3,
        "documents": [
            "Registration conditions and documents are set by your state's rules. The Ministry of Education's Guidelines for Regulation of Coaching Centres (sent to states on 16 January 2024) cover registration conditions and documents, fees, infrastructure, a code of conduct, student well-being, record keeping and grievance redressal",
            "Publish your fee, easy-exit and fee-refund policy on your website, as the guidelines require",
        ],
        "why": "The Ministry's 2024 guidelines ask states to regulate coaching centres through their own legal framework; some states (for example Rajasthan and Jharkhand in 2025) have passed their own laws. "
               "Separately, the Central Consumer Protection Authority's 2024 guidelines on misleading advertisements apply to coaching centres. Confirm what your state requires.",
        "portal_login": False,
    },
}
