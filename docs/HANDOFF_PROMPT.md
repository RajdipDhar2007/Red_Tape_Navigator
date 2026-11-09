# Handoff prompt for Claude Code (paste everything below into Claude Code)

You are taking over **Red Tape Navigator**, a web product that helps Indian citizens and small businesses (shops, bakeries, salons,
hotels, clinics, schools, small manufacturers, online sellers) work out which licences and registrations they need, interviews them
for the missing details, fills the official forms for them to review, and tracks follow-ups and renewals. Languages: English, Hindi,
Bengali. **`README.md` is the full description of the plan, the pipelines, what is done and how, and what is pending. Read it first.
This file tells you how to continue from exactly where the last contributor stopped.**

## YOUR MISSION (read this twice)
Take this app from its current state to a **finished, production-ready, launched business product**. **Do not stop, hand back, or
declare victory until every item in "What is LEFT" is done or is blocked ONLY by something a human must do.** When you are blocked on
a human, ask for exactly that thing (see "What ONLY THE HUMAN can do"), keep working on everything that does not depend on it, and resume
the moment they say it is done. Keep `docs/LAUNCH_CHECKLIST.md` current at all times (done / waiting on owner / blocked on third party).
Finish with a written final report: what is live, what is simulated, what remains, and the running costs. "Production ready" also means
business ready: it deploys, stays up, can be supported, is legally covered, is monitored and backed up, and the owner knows what it
costs and how it is funded.

## Rules you must follow
- **Verify before you claim.** Run the quality gates (below) and report failures honestly with their output. Never say "done" for
  something you did not run. If a check fails, fix the cause; never push past a red check.
- Commit and push to `main` after every verified change (all checks green). If the owner has not given you standing permission to
  push, ask once at the start and follow their answer. No pull requests, no new repos, no other GitHub actions unless the owner asks.
  **Do not add `.github/dependabot.yml`**: an earlier session did and GitHub opened 12 unwanted PRs.
- Never commit `.env*` (except `*.example`), `*.db`, secrets or keys. Never paste secrets in chat or in files that get pushed.
- Never type passwords, API secrets, OTPs, Aadhaar/PAN or payment details into any website, never create accounts, never solve CAPTCHAs,
  never accept terms for the owner, never submit forms or send emails/messages on their behalf. Those steps are the human's: tell them
  exactly what to click and what to paste where, then continue when they confirm.
- **Never invent legal facts** (fees, timelines, documents, rules) or API behaviour. Read the official page or document yourself (in a real
  browser, read-only) and record the source in `docs/RULES_VERIFICATION.md`. If it cannot be read, say so in the product text and ask the
  human to paste it. Every rule stays "verify with the authority" until an officer signs it off in the officer console.
- Never auto-submit anything to a government portal (CAPTCHA/OTP/Aadhaar login and terms forbid it). The product fills official PDFs and
  gives a "key-in sheet" for online-only portals; the citizen submits.
- Do not use the State Emblem of India (illegal under the 2005 Act). An authorised department may supply its emblem via `NEXT_PUBLIC_EMBLEM_URL`.
- Never run `npm run build` while `npm run dev` or `npm run start` is running (they share `.next`); stop servers first and check for stray
  `node`/`uvicorn` processes afterwards. Clean up test databases and stray processes when done. Do not stop servers that belong to other projects.
- **Keep the documentation true.** Whenever behaviour changes, update `README.md`, `docs/LAUNCH_CHECKLIST.md`, `docs/RULES_VERIFICATION.md`
  and this file in the same commit. At the end of each working session, add what you did and what is next so the following person can continue.
- The previous owner's personal machine preferences (drive letters, accounts) do not apply to your machine unless told.

## Snapshot at handoff (November 2026)
Backend 428 tests passing (about 95.7% coverage, gate 80%), evals pass (0 hallucinations), frontend lint/typecheck/5 unit tests/build pass,
7 Playwright e2e tests pass, CI has 7 jobs. 9 cities, 120 business types, 16 licences (liquor and drug licences are state-specific per city),
306 seeded rules, 3 languages (the backend text is translated too). Not deployed. Digio, MSG91 and all live integrations are built but untested
against the real services. Four Alembic migrations (0001 to 0004).

## Step 0: get the code and run it
1. Ask the owner (GitHub user `RajdipDhar2007`) to add you as a collaborator on the PRIVATE repo
   `https://github.com/RajdipDhar2007/Red_Tape_Navigator`, then clone it. Work on branch `main`.
2. Read, in this order: `README.md`, `docs/LAUNCH_CHECKLIST.md`, `docs/RULES_VERIFICATION.md`, `docs/INTEGRATIONS.md`,
   `docs/DEPLOYMENT_VERCEL_RENDER.md`, `docs/SECURITY.md`, `docs/COMPLIANCE.md`, `docs/ASSUMPTIONS.md`, `docs/RUNBOOK.md`, `docs/LOAD_TEST.md`,
   `docs/PILOT_PLAN.md`.
3. Backend (Python 3.12 or 3.13): `cd backend && python -m venv .venv`, activate, `pip install -e ".[dev]"`, then `ruff check .`, `mypy app`,
   `python -m pytest` (about 428 passing), `python -m evals.run` (golden cases and hallucination gate must pass).
4. Frontend (Node 20+, CI uses 22): `cd frontend && npm ci && npm run lint && npm run typecheck && npm test && npm run build`.
5. Run locally without Docker: in `backend` set `DATABASE_URL=sqlite+aiosqlite:///./dev_local.db`, run `alembic upgrade head`,
   `python -m app.kb.seed_loader`, `uvicorn app.main:app --port 8000`. In `frontend`: `npm run dev` (http://localhost:3000) or
   `npm run build && npm run start`. Backend CORS defaults to port 3000 only. Old local SQLite files are upgraded automatically on startup;
   production uses Alembic. After changing catalogue text, re-run the seed loader on an existing database.
6. Browser e2e: `cd frontend && npx playwright test` (ports 3000 and 8000 must be free; set `E2E_BACKEND_CMD` to your venv's uvicorn command if
   `python` is not the venv). It signs up a fresh account through the real UI. CI runs the same.
7. CI (`.github/workflows/ci.yml`): frontend, backend, backend on Postgres+pgvector, security scans incl. gitleaks, container build + scan,
   compose smoke, Playwright. **Keep it green.** Pushing again cancels the run in progress, so push once per verified change and wait for the
   result (`gh run list`, `gh run view`).

## Where things are (map of the code)
| Need | Look at |
|---|---|
| Goal parsing, typos, regulated sectors, clarify questions | `backend/app/agent/intake.py`, `backend/app/api/sessions.py` (`clarify`) |
| Plan and dependency order | `backend/app/agent/planner.py`, `backend/app/agent/research.py` |
| Licences, cities, business types | `backend/app/kb/catalog.py`, `sourced_licences.py` (state-specific `by_city`), `business_types.py` |
| Rules seeding and claims | `backend/app/kb/seed_loader.py`, `store.py`; allowlist `backend/config/sources.yaml` |
| Interview and validators | `backend/app/interview/` |
| Forms and official-PDF workflow | `backend/app/forms/` (`templates/*.json`) |
| Integrations (Digio, MSG91, SMTP) | `backend/app/integrations/` (`interfaces.py`, `mock.py`, `real/`), `backend/app/api/webhooks.py` |
| Translation of backend text | `backend/app/i18n_content/` (`data_hi.py`, `data_bn.py`), `backend/app/core/localize.py`, `frontend/lib/api.ts` |
| Interface strings | `frontend/messages/{en,hi,bn}.json`, `frontend/components/` |
| Production config checks | `backend/app/core/config.py` (`production_problems`) |
| Deployment | `render.yaml`, `docs/DEPLOYMENT_VERCEL_RENDER.md`, `docker-compose.prod.yml`, `backend/scripts/create_admin.py` |
| Tests | `backend/tests/` (19 files), `backend/evals/`, `frontend/e2e/` |

## What is DONE (all on `main`)
- **Core product:** sign-up/login (lockout, refresh-token rotation), DPDP consent, goal intake, cited plan, interview with validators and
  encrypted answers, form filling with provenance, review checkpoint, download, submission checklist, reminders, officer console, privacy
  export/erase and retention purge, audit log, prod config validation, privacy and terms pages in en/hi/bn.
- **Coverage:** 9 cities (Kolkata, Mumbai, Delhi, Bengaluru, Chennai, Hyderabad, Pune, Ahmedabad, Surat) and 120 business types, a baseline fallback that
  escalates to an officer, and accurate regulator notes for banks, insurance, post offices, ration shops and similar (never a wrong shop checklist).
- **Sourced licences read from official documents** (`sourced_licences.py`): liquor retail per state (West Bengal, Maharashtra, Delhi, Karnataka
  e-auction from the 01.07.2026 Gazette, Tamil Nadu, Telangana, Gujarat), retail drug licence (Delhi checklist and Drugs Rules), pet shop (final
  2018 Rules), clinic/hospital registration, bio-medical waste, school, college, coaching, BIS hallmarking. Sources and gaps are in
  `docs/RULES_VERIFICATION.md`.
- **Digio (Aadhaar e-Sign + DigiLocker):** adapters, signed webhook (HMAC `X-Digio-Checksum`, duplicates, optional IP list), `external_requests`
  table, `identity_providers` consent, UI in `DoneView.tsx`, 28 mocked-HTTP tests. **Never run against the real sandbox.**
  DigiLocker field mapping is deliberately not implemented (response shape unconfirmed).
- **MSG91 SMS adapter** (Flow API) unit-tested with a mock (one retry on network errors and 5xx/429, provider DLT error code kept for the operator, no retry on a rejection); never sent live. Digio read-only calls (status, download) retry once; creating a signature request is never retried.
- **Translations:** the whole interface and all backend text in Hindi and Bengali (about 275 strings per language), with tests. Native-speaker
  review is pending. Not translated: the officer console, the official PDFs, user-entered data.
- **Quality fixes this round:** follow-up question flow (a city answer is never a business type; earlier answers kept; typos like "resturent"
  and words like "cake" recognised), stale local SQLite schema auto-upgrade, licences added after a KB was seeded now load on demand, e2e tests
  rebuilt around real sign-up, gitleaks CI fix.
- **Deployment files:** `render.yaml`, Vercel guide, `docker-compose.prod.yml` + Caddy, first-officer script inside the image.

## What is LEFT (your work, in this order; skip nothing)
### A. Production deployment (the human logs in and holds the secrets; you guide, check and fix)
Follow the owner steps in `docs/LAUNCH_CHECKLIST.md` section 6 and `docs/DEPLOYMENT_VERCEL_RENDER.md`. After the human says it is live: check
`https://<api>/ready`, a real signup/login, a full business session, password-reset email, reminders, create the first officer, confirm database
backups and an uptime monitor, run the load test in `docs/LOAD_TEST.md` (Locust) and fix what it finds. Render has no India region (Singapore); if
the department needs in-India storage, move the backend to an Indian cloud and update `DATA_REGION` and the privacy text. Size the plans for traffic.
### B. Digio sandbox then production
Needs the human to obtain sandbox credentials. Then run the sandbox checklist in `docs/INTEGRATIONS.md`, fix request-shape differences, and
**implement the DigiLocker result mapping from a real `detail_response=true` response** (name, address, Aadhaar/PAN into answer keys with
`source="document"`, encrypted where sensitive). Only then production credentials and webhook IPs (`13.126.198.236`, `52.66.66.81`).
### C. MSG91 SMS
After the human completes DLT approval, put `MSG91_AUTHKEY` and `MSG91_TEMPLATE_ID` in Render, send a real test SMS to the human's own number,
and fix the adapter if the live shape differs (DLT errors 203/211 mean sender/template not approved).
### D. Rules verification (most important for trust)
Fill gaps **only from official pages you read**: Karnataka's 03.07.2026 amendment and any later liquor auction round; current Maharashtra and
Telangana liquor notifications; each pilot state's own clinical-establishment law; state school and coaching registration forms; UGC and university
affiliation rules; GST fee, timeline and current per-state goods threshold; FSSAI 2026 fee slabs; trade-licence fee schedules for Pune, Ahmedabad,
Mumbai, Delhi, Bengaluru, Chennai, Kolkata; shops-and-establishments fees and timelines per state; fire-safety and pollution-board pages outside
West Bengal; a cited source for every timeline; Gujarat health-permit rules. Government sites often block bots: use a real browser (read-only);
if still unreadable, ask the human to paste the page. After each addition: tests, translation rows, `docs/RULES_VERIFICATION.md`, re-export
`docs/RULES_REVIEW_EXPORT.csv`. With `ANTHROPIC_API_KEY`/`ANTHROPIC_MODEL` set and `DEMO_MODE=false`, `POST /admin/refresh` extracts grounded claims
(the quote must appear on the page). A reviewer then marks each rule verified/corrected/rejected in the officer console.
### E. Official forms
The 3 bundled PDFs are watermarked placeholders. After the human gets FSSAI's permission, officers fetch Form A and Form B through the officer console
(allowlisted URLs: Form A `https://foscos.fssai.gov.in/assets/docs/registrationForm_A.pdf`, Form B state `https://foscos.fssai.gov.in/assets/docs/stateForm_b.pdf`,
Form B central `https://fcstraining.fssai.gov.in/assets/docs/centralForm_b.pdf`), you write the field-map JSON in `backend/app/forms/templates/`, and an
officer approves it. FSSAI and Udyam registration are online-only, so keep the key-in sheet. Other departments need their own written permission.
### F. Language quality
Native Hindi and Bengali review of `backend/app/i18n_content/data_hi.py`, `data_bn.py` and `frontend/messages/*.json` (legal and fee wording first).
Hindi and Bengali keywords for all business types are done (`_LOCAL_KEYWORDS`, pending native review); the officer console is already translated (`staff.*` in all three message files).
### G. Launch hardening
Counsel review of privacy/terms/DPDP consent text, then `NEXT_PUBLIC_LEGAL_REVIEWED=true` on Vercel. Real-phone, slow-network, voice-input and
screen-reader tests. Penetration test or at least the `docs/SECURITY.md` checklist, secrets-rotation plan, backup-restore drill, move browser tokens
from `sessionStorage` to httpOnly cookies behind a BFF, consider MFA/OIDC, design CSC-operator delegation, decide LLM egress/residency with counsel.
Pilot with 5-10 real shop owners (`docs/PILOT_PLAN.md`), collect feedback, fix, then launch.
### H. Business readiness (ask the owner; decisions, not code)
Who pays and how (free for citizens funded by a department/CSC programme, subscription, per use)? Support channel and response times, an on-call
contact (`docs/RUNBOOK.md`), a monthly cost estimate (Render plans, Postgres, SMTP, MSG91 per SMS, Digio per signature and DigiLocker call, LLM usage),
a custom domain, SPF/DKIM/DMARC, and a data-processing agreement with each provider. Write the answers into `docs/`, wire any configuration they imply,
and put the cost table in the final report.
### I. Optional
WhatsApp and UMANG real adapters (mocked today), more cities and business types, e-Sign for additional forms, analytics.

## What ONLY THE HUMAN can do (ask for each one; give exact click-by-click steps; wait for "done")
Never do these yourself and never ask the human to paste a secret into chat: they put values into Render/Vercel/`.env.prod`.
1. **MSG91 (SMS):** complete KYC, register on a telecom operator's TRAI DLT portal (Airtel, Vi, BSNL, STPL or Tata) as an entity, register a
   6-character sender ID of their choice and the template `Red Tape Navigator reminder: {#var#}` (service-implicit/transactional, ONE variable),
   link them in MSG91 (Sender Id and Templates pages), create a MSG91 Flow from the template, then copy the Template ID and Auth Key into Render.
   Ask them to tell you when approved so you can test a real SMS.
2. **Digio:** submit the "Get in Touch" form at https://www.digio.in with the official business email (reCAPTCHA; if the form errors, retry from
   another network or email Digio) asking for sandbox (UAT) client id/secret, DigiLocker via DigiStudio with template `DIGILOCKER_AADHAAR_PAN`,
   Aadhaar eSign enabled, and production onboarding requirements. Credentials go into Render, never chat. They also set the webhook URL
   `https://<api>/webhooks/digio` and secret in Digio's enterprise dashboard (Profile > Webhooks).
3. **Deployment logins and secrets:** generate `SECRET_KEY` and `FIELD_ENCRYPTION_KEY` (`make keygen`) on their machine and BACK UP the encryption key
   (losing it destroys stored Aadhaar/PAN answers); create an SMTP account with a verified sender domain (SES, Brevo, SendGrid or NIC mail); sign in to
   Render (New > Blueprint > this repo > `render.yaml`) and Vercel (Add New Project > Root Directory `frontend` > `NEXT_PUBLIC_API_URL`); fill the
   `sync:false` env vars; set `CORS_ORIGINS` and `WEB_BASE_URL` to the Vercel https origin; create the first officer in the Render shell with
   `ADMIN_PASSWORD='...' python /app/scripts/create_admin.py officer@their-domain admin`; enable Postgres backups and an uptime monitor on `/ready`.
4. **FSSAI:** email `helpdesk-foscos@fssai.gov.in` asking permission to reproduce Form A and Form B; the reply is the proof. Tell you when they answer.
5. **Counsel and reviewers:** legal review of the privacy and terms text; native Hindi and Bengali review; rule sign-off in the officer console using
   `docs/RULES_REVIEW_EXPORT.csv`.
6. **Set a real `GRIEVANCE_CONTACT`** (the DPDP grievance officer shown to citizens). Production refuses to start without it.
7. **Business decisions** (section H), a real-phone/slow-network test, and the 5-10 shop-owner pilot.
8. **Optional:** an Anthropic API key (`ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`) for the live rules refresh. It costs API usage.

## How to work (the loop to repeat until done)
1. Pick the next unfinished item above (or the next red item in `docs/LAUNCH_CHECKLIST.md`).
2. Read the relevant official sources or docs first; write down the source.
3. Implement with tests (mocked HTTP for integrations; add translation rows for any new user-visible text).
4. Run every gate: `ruff check .`, `mypy app`, `python -m pytest`, `python -m evals.run`; `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`,
   `npx playwright test` (ports free).
5. Update README, `docs/LAUNCH_CHECKLIST.md`, `docs/RULES_VERIFICATION.md` and this file; commit; push; watch CI for that exact commit.
6. Report plainly: what changed, what you verified, what is still unverified, what you need from the human.

## Gotchas learned the hard way
- The message "Could not sign in. Check your details." is shown for ANY failed auth call, including a server 500 (for example an outdated local
  database). Check the API response before blaming credentials.
- Many Indian government sites reset connections or block non-browser clients (GST portal, some municipal and state sites; one state excise site fails
  the command-line TLS handshake but opens in a browser). This does not mean a rule is wrong. Never bypass a firewall or CAPTCHA.
- Digio's API docs are JavaScript-rendered with content in a shadow DOM; read them in a real browser. The Digio IP allowlist can be forged through
  `X-Forwarded-For`; the HMAC checksum is the real control.
- The KB only re-seeds a licence that has no claims; after changing catalogue text re-run `python -m app.kb.seed_loader` on an existing database.
- The e2e suite uses ports 3000 and 8000 and reuses a server only if it answers `/ready`; another project on port 8000 once broke every sign-up test.
- CI cancels in-progress runs when you push again; the gitleaks step needs full history (`fetch-depth: 0`, already set).
- Windows: write multi-line Python edits to a script file and run it; quoted heredocs break in some shells. Docker is often not running locally; the
  compose stack is verified by the CI `compose-smoke` job.

## Definition of done (all must be true before you stop)
All tests, lint, types, evals, e2e and CI green; production live on HTTPS with real SMTP, MSG91 and Digio (production credentials, sandbox-tested first);
core rules verified by a reviewer and every other rule still labelled "verify with the authority"; official forms loaded with permission where
available; privacy/terms approved and the draft banner off; no demo labels visible in production (`DEMO_MODE=false`); backups, uptime monitoring, load
test and security checklist done; pilot feedback addressed; README and docs updated; `docs/LAUNCH_CHECKLIST.md` fully resolved; everything committed and
pushed to `main`; and a final written report listing what is live, what is simulated, what remains, and the monthly running costs.

## First message to the human (send this when you start)
Confirm you have repo access and CI is green, then list the eight items under "What ONLY THE HUMAN can do", ask which they have already done, and start
immediately on everything that does not depend on them (sections D, F and the code parts of B and C).

## Session log: 2026-11-09 (demo-readiness round)
Owner instruction: push to `main` after every verified change; human-only steps (section "What ONLY THE HUMAN can do") are deferred until the demo is selected.
Done: Hindi/Bengali keywords for about 75 business types; FSSAI 2026 fee slabs and turnover thresholds (FoSCoS list updated 01.04.2026, order 13.03.2026); GST registration timeline from CGST Rule 9 (7 working days) and thresholds re-confirmed from CBIC; Kolkata trade licence fee examples from the KMC 2026-27 chart. All sourced in `docs/RULES_VERIFICATION.md`; review export regenerated. Gates: ruff, mypy, 373 tests, evals, frontend lint/typecheck/unit/build, 5 Playwright tests all green.
Lesson: a `cmd | tail` in an `&&` chain hides a failing pytest; check the exit status before committing.
Next: trade-licence fees for Pune, Ahmedabad, Mumbai, Delhi, Bengaluru, Chennai; shops-and-establishments fees per state; fire/pollution pages outside West Bengal; keywords for the remaining ~37 types; then the human-dependent items.

### Session log: 2026-11-09 (continued: more rules, hardening, UX, Surat)

- Rules added from official text: Chennai shops-act fee (G.O. Ms. No. 55 of 2024), Mumbai eating-house and hair-saloon licence fees (MCGM Section 394 schedule),
  Maharashtra fire-fee structure (Act 2006 s.11, s.13, no rates), pollution White-category intimation (MPCB page). Not added (no official text): Karnataka shop fees,
  Maharashtra and Gujarat shop fees, Jaipur and Lucknow as cities. See `docs/RULES_VERIFICATION.md`.
- Surat added as a ninth city (authority and portal only; Gujarat state sources reused).
- MSG91 and read-only Digio calls retry once; creating a signature request is never retried.
- UX: `frontend/components/fx/` (Reveal, CountUp, Confetti, ProgressRing), tick-off checklist, typing indicator, dashboard badges, print/copy/WhatsApp share.
  A temporary Playwright spec was used to take screenshots and then deleted; do the same for visual checks (the e2e config starts both servers).
- Lesson: in a PowerShell/bash tool call, a Python edit script that needs a backslash-n inside a TS string must build it with `chr(92)`; a doubled backslash was turned into a real newline.

### Session log: 2026-11-09 (browser pass with the owner's Chrome)

- Karnataka (e-Karmika home page), Maharashtra (2018 Rules PDF, English text) and Gujarat (2020 Rules, a scanned PDF checked as an image; Act 1 of 2026 for the new
  threshold) shop-registration fees were read from official sources and added. Not readable in Chrome: site.bbmp.gov.in (did not load), the AMC site (froze the tab).
  Chennai's revised trade fee exists only in news reports. After a frozen tab, close it and open a new one with `tabs_context_mcp` (createIfEmpty).
- App test in Chrome against local servers (production build, DEMO_MODE): signup with a throwaway account, consent, a Surat parlour goal, the plan, ticking steps
  (progress ring, "Next up"), Hindi view with the ticks kept, no console errors. A claim whose confidence is 0.8 shows no "Verify with the authority" chip
  (the chip appears below the confidence threshold); officially-read rules are capped at 0.8, so they look verified until a reviewer acts. Consider showing a "pending review" tag.
- Defect found and fixed: the Gujarat fee cited the municipal site as its source; the rule text now names col.gujarat.gov.in.

### Session log: 2026-11-09 (fourth pass: pollution fees, review label, fire validity, clinic laws)

- New rule mechanisms: `fee_by_city` on pollution_consent (city-scoped, with `NATIONAL_FALLBACK` for other cities), `timeline_by_city` (Delhi fire certificate validity), clinical_registration `by_city` entries.
- UI: every citation now shows "Awaiting expert review" (confidence under 0.9) or "Expert-reviewed" (0.9 or more, set when a reviewer verifies it), next to the "Verify with the authority" flag. Strings in en/hi/bn.
- PITFALL: before `npx playwright test`, kill every leftover `next start` and `uvicorn` process (PowerShell: Get-CimInstance Win32_Process, match the command line). A stale `next start` from an earlier test pass kept port 3000 after I rebuilt `.next`, served the old HTML with missing chunks, and all 5 e2e tests failed with "Application error: a client-side exception". Playwright reuses a server it finds on the port (`reuseExistingServer` is on outside CI).
- Writing multi-line Unicode edit scripts: use the Write tool to create the .py file, not a bash heredoc (a long heredoc with quotes made bash fail with "unexpected EOF").

