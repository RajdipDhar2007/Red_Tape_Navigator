# Pilot plan: one municipality, one use case

## Scope
* **Municipality:** Kolkata Municipal Corporation (KMC), West Bengal. (Bengali-first; the seed pack already has KMC data.
  Choose another city if a partner relationship exists there: the design is city-agnostic.)
* **Use case:** a new **small food business** (bakery, tea stall, sweet shop, home kitchen) needing
  **Udyam → FSSAI registration/licence → KMC trade licence** (+ fire safety NOC where applicable).
* **Users:** first-time entrepreneurs, supported at 2–3 Common Service Centres (CSCs) and also self-serve.
* **Duration:** 12 weeks. Target 150 completed journeys.
* **Out of scope:** any submission by the system, GST filing, payments, other municipalities.

## Preconditions (must be true before real citizens use it)
1. Seed rules replaced by **human-verified** claims for KMC + FSSAI + Udyam (domain expert signs off; review queue empty
   for the pilot scope; every claim has a source and a verification date).
2. The three real forms added (see INTEGRATIONS) after confirming redistribution rights; placeholder banner removed.
3. Written agreement with KMC (or a letter of no-objection) and with the CSC operator(s).
4. DPIA, privacy notice, grievance officer, DPO decision; legal sign-off on Aadhaar handling (COMPLIANCE.md).
5. Security audit/pen-test of the deployed stack; India-region hosting; backups tested.
6. `DEMO_MODE=false`, `INTEGRATIONS_MODE` set only for integrations that are actually approved (otherwise mocks stay
   labelled, or the features are hidden).

## Roles
| Role | Who | Does |
|---|---|---|
| Citizen | entrepreneur | uses the tool, signs and submits themselves |
| CSC operator | CSC staff | assists citizens, resolves low-confidence items |
| Reviewer | domain expert / KMC liaison | verifies claims, owns the rules pack |
| Admin | platform team | operations, privacy requests |

## Success metrics
| Metric | Target | How measured |
|---|---|---|
| Citation coverage of shown claims | 100 % | eval gate + production sample audit |
| Factual accuracy of fees/timelines/documents vs. authority (weekly reviewer spot-check of 30 claims) | ≥ 95 % correct | reviewer log |
| Journeys reaching "reviewed & downloaded" | ≥ 60 % of started | analytics (events only, no PII) |
| Median active time goal → reviewed forms | ≤ 25 min (baseline: self-service ~2–3 h of research) | timestamps |
| Questions asked per journey vs. minimum union | ≤ 1.1× | interview logs (keys only) |
| Form field correctness (fields the citizen edited at review ÷ total) | edit rate ≤ 15 % | review events |
| Applications later **rejected for missing/incorrect documents** among those who tell us the outcome | ≥ 30 % lower than the CSC's historical rate | follow-up survey |
| Citizen satisfaction (CSAT, 1–5) | ≥ 4.2 | in-app/operator survey |
| Language use | ≥ 40 % of journeys in bn/hi | locale |
| Safety: submissions made by the system | exactly 0 | by construction + audit |
| Incidents: PII leaks, uncited claims shown | 0 | monitoring |
| Escalations resolved within 1 business day | ≥ 90 % | review queue timestamps |

## Timeline
| Weeks | Activity |
|---|---|
| −6 to 0 | Preconditions: verification of rules, forms, agreements, DPIA, security test |
| 1–2 | Soft launch with 2 CSC operators, 20 journeys; daily review of escalations; fix top issues |
| 3–8 | Widen to 3 CSCs + self-serve; weekly rules refresh and diff review; weekly accuracy sample |
| 9–11 | Stabilise; measure outcomes (rejections, time saved) via follow-up |
| 12 | Evaluation report, go/no-go for next municipality |

## Go / no-go criteria for scaling
* All safety metrics at 0; accuracy ≥ 95 %; CSAT ≥ 4.2; rejection-rate improvement demonstrated;
  grievance log has no unresolved privacy complaints; regulator/municipality comfortable with continuing.

## Risks
| Risk | Mitigation |
|---|---|
| Rules change silently | weekly refresh + diff detection + review queue; show "last checked" date next to every claim |
| Wrong guidance causes a rejected application | confidence flags, "verify with authority", human escalation, disclaimer on every output |
| Aadhaar handling risk | encrypt/mask, minimise, consider not collecting; legal sign-off |
| Portal changes/captcha | human handoff; no scraping behind logins |
| Over-reliance on AI | reviewer-in-the-loop for low confidence; citizen must confirm review before downloads |
| Low literacy / connectivity | bn/hi UI, voice input, low-data mode, CSC-assisted flow |

## DPIA outline
Purpose and necessity → data inventory (COMPLIANCE.md) → flows (ARCHITECTURE.md) → risks to principals (misuse of
Aadhaar/PAN, wrong advice, profiling) → mitigations (above) → residual risk and approval.
