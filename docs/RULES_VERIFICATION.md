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

## Business types without a licence checklist (handled as notes, not rules)
Banks, NBFCs/microfinance, insurance, stock brokers/mutual funds, forex dealers, pharmacies, liquor shops, firecracker shops,
fertiliser/pesticide shops, clinics/hospitals, schools/colleges, taxi/transport, telecom/ISP, post offices and ration (fair price)
shops are recognised by word match in `REGULATED_SECTORS` (`backend/app/kb/catalog.py`). The product names only the regulator
(a stable fact), shows the basic premises registrations, and queues an officer. It states no fees, timelines or conditions for them.
Ration shops are "authorised" by the state, post offices are "operated" by India Post. A reviewer should confirm each regulator name.

## Not confirmed (need a reviewer or the authority; do not guess)

- **GST registration fee and timeline**, and the **per-state goods threshold today**: gst.gov.in/tutorial.gst.gov.in block automated and in-page fetches
  (firewall rejection); a reviewer should read the registration FAQ on the portal.
- **FSSAI fees and validity** (changed in 2026): FoSCoS calculates the fee per business type; a reviewer should record the current slabs.
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
