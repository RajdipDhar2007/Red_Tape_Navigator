# Rules verification log

Every rule in the pack stays **"verify with the authority"** until an officer signs it off in the officer console
(`/en/staff`). This log records what was checked against official pages, so reviewers do not start from zero.
Worksheet for reviewers: [`RULES_REVIEW_EXPORT.csv`](RULES_REVIEW_EXPORT.csv) (regenerate with
`python scripts/export_rules_for_review.py docs/RULES_REVIEW_EXPORT.csv`; 168 rules, all UNVERIFIED, reviewer columns empty).

## What the automated check can and cannot say (2026-11-08)

`make verify-sources` result: 26 cited sources, 11 unreachable or blocked from a bot (several Indian government sites
reset connections or return errors to non-browser clients; this says nothing about whether the rule is right).
Most claims are deliberately qualitative ("fee varies; confirm with the authority"), so there is no number to match; the
tool now reports how many claims are numeric. A human reviewer is needed for the rest. The tool never marks anything verified.

## Checked by reading the official page in a browser (read-only)

| Claim | Evidence | Result |
|---|---|---|
| Udyam registration is free | udyamregistration.gov.in home page: "Udyam (MSME) Registration is Free of Cost and paperless" | Confirmed (2026-11-08) |
| GST registration thresholds | CGST Act s.22 (taxinformation.cbic.gov.in): Rs 20 lakh general, Rs 10 lakh special category states; goods-only suppliers may be raised up to Rs 40 lakh by notification. A CBIC 2019 update listed states that kept Rs 20 lakh for goods, including Telangana | Wording corrected in the pack; current per-state limit still to be confirmed by a reviewer on the GST portal |
| Hyderabad trade licence | ghmc.gov.in/Trade.aspx: online application with OTP login, fee paid online, certificate "issued instantly" after payment; fee amounts are in a separate "Trade License Fee rates" PDF | Source URL now the exact page. The fee table PDF was read: per sq ft by road width, Rs 3 (single lane, 20 ft), Rs 4 (double lane, 30 ft), Rs 6 (multiple lanes, wider than 30 ft). It does not say if this is yearly or whether other charges apply, so the pack says exactly that; reviewer to confirm |
| Gold / jewellery shops (BIS hallmarking) | bis.gov.in/hallmarking-jewellers: jewellers apply online on the NSWS portal (reachable via manakonline.in); "No fee is being charged from jewellers for grant of registration/certification"; certificate granted instantly and valid for life; hallmarked jewellery carries the BIS mark, purity (carat/fineness) and a six-digit HUID. The page lists no documents; per-article hallmarking charges (Rs 45 in the Jan 2024 jeweller guidelines, Rs 35 in the 2021 version) change over time | Added as licence `bis_hallmark` with the fee/timeline wording above; per-article charges and the list of districts where hallmarking is mandatory NOT stated (reviewer to confirm) |
| Ahmedabad shops & establishments | ahmedabadcity.gov.in/StaticPage/shops_establishment: AMC administers it; Form A for 10+ workers, Form D intimation for fewer; forms downloadable; no fee, timeline or online process stated | Authority and URL corrected to AMC |

## Licences read from official documents (2026-11-08), added with their sources

These are in `backend/app/kb/sourced_licences.py`. Every claim built from them stays flagged "verify" (confidence below 0.9)
until an officer signs it off. Where a page could not be read or says nothing, the pack says so instead of guessing.

| Licence | Official source read | What the pack states | Not found / caveats |
|---|---|---|---|
| Liquor retail, Kolkata (West Bengal) | excise.wb.gov.in, public licence application page | Online application, choose police station, upload applicant and site documents (16 items listed), pay the application fee through GRIPS | Fee amount, timelines and how an LOI is obtained are not on the page |
| Liquor retail, Mumbai and Pune (Maharashtra) | stateexcise.maharashtra.gov.in FL-II and FL/W-II pages | FL-II: application fee Rs 2,000 (population above 1 lakh) or Rs 1,000, Form FL/A-IB, location and solvency certificate, affidavit of no tax dues, plans; page says "There is ban on grant of new license" | Pages last reviewed 23/09/2014; licence fee on a separate page not read; FL/W-II is only for wine manufacturers |
| Liquor retail, Delhi | excise.delhi.gov.in licences page | L-6 retail vends are granted only to selected Delhi government undertakings; licence fee Rs 2,50,000; premises conditions | No private route described; L-7 and L-9 are named but not described |
| Liquor retail, Bengaluru (Karnataka) | Karnataka Gazette (Extraordinary) Part IV-A No. 479 of 01.07.2026, notification FD 52 EFL 2025, read in Chrome (stateexcise.karnataka.gov.in/uploads/E-auction Notification 01-07-2026, 55 pages) | New CL-2A (retail) and CL-9A (bar) licences are allotted by e-auction on MSTC's portal: registration Rs 1,000 + GST, application fee Rs 50,000 (non-refundable), EMD 2% of base price, bid steps Rs 2 lakh; Bengaluru ranges (GBA): base price Rs 1.5 crore, licence fee Rs 9,00,000, EMD Rs 3,00,000 (Annexure-5); winner pays 0.42% + GST to MSTC and at least 50% of the bid; first-year licence fee waived; five-year term 2026-27 to 2030-31; reservation 5.25/5.25/4.50/3% | The first round for Bengaluru ran in late July 2026; the 03.07.2026 amendment, Annexures 1-4 in full and any later round were not read; the site fails a command-line secure connection, so it was read in a browser |
| Liquor retail, Chennai (Tamil Nadu) | cpe.tn.gov.in, Tamil Nadu Liquor Retail Vending (in Shops and Bars) Rules, 2003 | Retail licence is held by the state corporation (TASMAC) | Rules are old; current policy and bar licences not read |
| Liquor retail, Hyderabad (Telangana) | excise.telangana.gov.in, G.O.Ms.No.86 of 01.08.2023 and its application form | Shops allotted by lottery; 2023-25 application fee Rs 2,00,000 non-refundable; documents list | Notification for the current period was not found |
| Liquor, Ahmedabad (Gujarat) | Gujarat Prohibition Act, 1949 (indiacode.nic.in) and the department's site | Prohibition state; sale barred unless a licence or permit allows; health permits under section 40A | Current rules and fees for health permits not read |
| Pet shop registration | awbi.gov.in, Prevention of Cruelty to Animals (Pet Shop) Rules, 2018 (final text, read from the PDF) | Registration with the State Animal Welfare Board; Rs 5,000 non-refundable fee, a separate application per premises; valid five years; renewal Rs 5,000, apply 30 days before expiry; inspection by a State Government veterinarian | A MoEF draft copy says two years; the final text says five years (final text used) |
| Retail drug (pharmacy) licence | drugs.delhi.gov.in retail checklist (Forms 20, 21, 20F) and the Drugs Rules, 1945 on cdsco.gov.in | Delhi's full document list; for other cities the same list marked "based on Delhi's checklist"; 10 sq m premises (15 sq m for both form pairs); registered pharmacist | Other states' checklists, fee amounts and timelines not read |
| Clinic / hospital / lab registration | clinicalestablishments.mohfw.gov.in FAQ | Who is covered; the central Act is in force only in listed states and Union Territories (not these pilot states except where adopted); two-step registration where it applies | Each pilot state's own law and authority were not read; fees and validity not stated in the FAQ |
| Bio-medical waste authorisation | cpcb.nic.in and the Bio-Medical Waste Management Rules, 2016 (search summaries) | Every occupier must get authorisation from the State Pollution Control Board, irrespective of quantity | Form, fee and validity not confirmed |
| School recognition | CBSE affiliation bye-laws and FAQ (cbse.gov.in), RTE Act section 18 as quoted there | State recognition certificate is required; CBSE affiliation is optional, via SARAS, with the recognition certificate and a State NOC | State forms and fees not read; building and fire approvals differ by state |
| College / technical institution | aicte-india.org approval-process pages | AICTE approval for technical institutions via the NSWS portal, annual cycles | UGC and university affiliation rules were not read |
| Coaching centre | PIB release of a Parliament answer on the Ministry of Education guidelines of 16 January 2024 | Guidelines ask states to regulate; some states (Rajasthan, Jharkhand 2025) passed laws | Your state's rules and fees not read |

## Business types (112)

`backend/app/kb/business_types.py` maps about 100 more business types onto licence sets that are already in the pack (retail, food retail,
food service, office, manufacturing, warehouse, online). It adds no new legal claims. Types known to need extra permits that are NOT in the pack
(meat and fish shops, banquet halls, garment and food-processing units, travel agencies and more) carry `coverage="specific"`: the app shows a note
and queues an officer. Matching is by English keywords (longest match wins); `tests/test_catalog_integrity.py` checks every keyword and type.

## Business types without a licence checklist (handled as notes, not rules)
Banks, NBFCs/microfinance, insurance, stock brokers/mutual funds, forex dealers, firecracker shops, fertiliser/pesticide shops and pest control,
taxi/transport, telecom/ISP, real-estate agents, driving schools, security agencies, professional practices (law, accounting, architecture,
veterinary), post offices and ration (fair price) shops are recognised by word match in `REGULATED_SECTORS` (`backend/app/kb/catalog.py`). The product names only the regulator
(a stable fact), shows the basic premises registrations, and queues an officer. It states no fees, timelines or conditions for them.
Ration shops are "authorised" by the state, post offices are "operated" by India Post. A reviewer should confirm each regulator name.

## Not confirmed (need a reviewer or the authority; do not guess)

- **GST registration**: timeline RESOLVED 2026-11-09 from CBIC taxinformation.cbic.gov.in CGST Rule 9(1): officer to approve a complete application "within a period of seven working days" (deficiency notice REG-03 adds time). Thresholds re-confirmed from the CBIC "GST An Update" (cbic-gst.gov.in/pdf/01052019-GST-An-Update.pdf): goods Rs 40 lakh (Rs 20 lakh in Arunachal Pradesh, Manipur, Meghalaya, Mizoram, Nagaland, Puducherry, Sikkim, Telangana, Tripura, Uttarakhand), services Rs 20 lakh (Rs 10 lakh in Manipur, Mizoram, Nagaland, Tripura), effective 01.04.2019; that document is from 2019 so a reviewer must check for later changes. The registration fee ("free") is not stated on the rule page and still needs the GST portal FAQ (portal blocks automated reads).
  (firewall rejection); a reviewer should read the registration FAQ on the portal.
- **FSSAI fees and validity**: RESOLVED on 2026-11-09 from foscos.fssai.gov.in "Kind of Business" list (updated 01.04.2026) and FSSAI order dated 13.03.2026 (thresholds effective 01.04.2026): registration Rs 100 (turnover up to Rs 1.5 crore), State licence Rs 5,000 (above Rs 1.5 crore to Rs 50 crore), Central licence Rs 7,500 (above Rs 50 crore); hawker registration Rs 0; importer, e-commerce, five-star hotel need a Central licence. The 10.03.2026 amendment provides perpetual validity subject to risk-based inspections; how FoSCoS applies it was not confirmed, and the product says so. Still marked "verify with the authority" until a reviewer signs off.
- **Fire safety NOC** and **pollution control (CTE/CTO)** sources for Maharashtra, Delhi, Karnataka, Tamil Nadu, Telangana and Gujarat:
  searches of government domains found portals for other states only. The department or its single-window portal must supply the exact page.
  (The pack currently cites each state's general government home page for fire NOC and the CPCB home page for pollution; treat these as placeholders.)
- **Trade licence fees**: Pune (PMC), Ahmedabad (AMC), Mumbai, Delhi, Bengaluru, Chennai, Kolkata: fee schedules not yet read. (Hyderabad: table read, see above.)
- **Shops & establishments** fees and timelines for every state.
- Timelines quoted in the pack ("about 7 days", "3-7 working days", etc.) have no cited official source yet.

## Next step with an LLM (needs your API key)

With `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL` set and `DEMO_MODE=false`, an admin can `POST /admin/refresh` to extract claims
whose quote must appear verbatim on the official page; low-confidence or changed claims then land in the review queue.
That costs API usage and sends public page text to the provider, so it is left for you to switch on.
