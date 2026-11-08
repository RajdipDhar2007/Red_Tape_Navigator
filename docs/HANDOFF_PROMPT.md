# Handoff prompt for Claude Code (paste everything below into Claude Code)

You are taking over **Red Tape Navigator**, a web product that helps Indian citizens and small businesses (shops, bakeries,
salons, small manufacturers, online sellers) work out which licences and registrations they need, interviews them for the
missing details, fills the official forms for them to review, and tracks follow-ups and renewals. Languages: English, Hindi,
Bengali.

## YOUR MISSION (read this twice)
Take this app from its current state to a **finished, production-ready, launched business product**. **Do not stop, hand
back, or declare victory until every item in "What is left" is done or is blocked ONLY by something a human must do.**
When you are blocked on a human, ask for exactly that thing (see "What only the human can do"), keep working on everything
that does not depend on it, and resume the moment they say it is done. Keep `docs/LAUNCH_CHECKLIST.md` current at all
times (done / waiting on owner / blocked on third party). Finish with a written final report: what is live, what is
simulated, what remains, and the running costs. "Production ready" also means business ready: it deploys, stays up, can be
supported, is legally covered, is monitored and backed up, and the owner knows what it costs and how it earns or is funded.

## Rules you must follow
- Verify before you claim: run the checks (below) and report failures honestly with their output. Never say "done" for
  something you did not run.
- Commit and push to `main` after every verified change (all checks green). If the owner has not given you standing
  permission to push, ask once at the start and follow their answer. No pull requests, no new repos, no other GitHub actions
  unless the owner asks. **Do not add `.github/dependabot.yml`**: an earlier session did and GitHub opened 12 unwanted PRs.
- Never commit `.env*` (except `*.example`), `*.db`, secrets or keys. Never paste secrets in chat or in files that get pushed.
- Never type passwords, API secrets, OTPs, Aadhaar/PAN or payment details into any website, never create accounts, never
  solve CAPTCHAs, never accept terms for the owner, never submit forms or send emails/messages on their behalf. Those steps
  are the human's: tell them exactly what to click and what to paste where, then continue when they confirm.
- Never invent legal facts (fees, timelines, rules) or API behaviour. If an official page cannot be read, ask the human to
  paste it. Every rule stays "verify with the authority" until an officer signs it off in the officer console.
- Never auto-submit anything to a government portal (CAPTCHA/OTP/Aadhaar login and terms forbid it). The product fills
  official PDFs and gives a "key-in sheet" for online-only portals; the citizen submits.
- Do not use the State Emblem of India (illegal under the 2005 Act). An authorised department may supply its emblem via
  `NEXT_PUBLIC_EMBLEM_URL`.
- Never run `npm run build` while `npm run dev` or `npm run start` is running (they share `.next`); stop servers first and
  check for stray `node`/`uvicorn` processes afterwards. Clean up test databases and stray processes when done.
- The owner's personal machine preferences (drive letters, accounts) do not apply to the friend's machine unless told.

## Step 0: get the code and run it
1. Ask the owner (GitHub user `RajdipDhar2007`) to add you as a collaborator on the PRIVATE repo
   `https://github.com/RajdipDhar2007/Red_Tape_Navigator`, then clone it. Work on branch `main`.
2. Read, in this order: `README.md`, `docs/LAUNCH_CHECKLIST.md`, `docs/INTEGRATIONS.md`, `docs/DEPLOYMENT_VERCEL_RENDER.md`,
   `docs/RULES_VERIFICATION.md`, `docs/SECURITY.md`, `docs/COMPLIANCE.md`, `docs/ASSUMPTIONS.md`, `docs/RUNBOOK.md`,
   `docs/LOAD_TEST.md`, `docs/PILOT_PLAN.md`.
3. Backend (Python 3.12 or 3.13): `cd backend && python -m venv .venv`, activate, `pip install -e ".[dev]"`, then
   `ruff check .`, `mypy app`, `python -m pytest` (expect about 146 passing, coverage about 95%, gate is 80%),
   `python -m evals.run` (golden cases and hallucination gate must pass).
4. Frontend (Node 20+): `cd frontend && npm ci && npm run lint && npm run typecheck && npm test && npm run build`.
5. Run locally without Docker: in `backend` set `DATABASE_URL=sqlite+aiosqlite:///./dev_local.db`, run
   `alembic upgrade head`, `python -m app.kb.seed_loader`, `uvicorn app.main:app --port 8000`. In `frontend`: `npm run dev`
   (http://localhost:3000) or `npm run build && npm run start`. Backend CORS defaults to port 3000 only. Old local SQLite
   files are upgraded automatically on startup (columns are added); production uses Alembic.
6. Browser e2e: `cd frontend && npx playwright test` (set `E2E_BACKEND_CMD` to your venv's uvicorn command if `python` is not
   the venv). It signs up a fresh account through the real UI. CI runs the same.
7. CI (`.github/workflows/ci.yml`) has 7 jobs (frontend, backend, backend on Postgres+pgvector, security scans incl. gitleaks,
   container build + scan, compose smoke, Playwright). **Keep it green.** Pushing again cancels the run in progress, so push
   once per verified change and wait for the result with `gh run list` / `gh run view`.

## What the product is (architecture in one paragraph)
FastAPI backend (`backend/app`) + Next.js 15 frontend (`frontend`, next-intl en/hi/bn) + PostgreSQL with pgvector (SQLite for
local dev) + optional Redis; a worker process for reminders and form re-checks. Flow: sign up/login -> consent (DPDP) ->
describe the goal -> intake understands business type and city -> research agent returns a cited step-by-step plan from the
rules knowledge base -> interview asks only what is missing (validators for PAN, Aadhaar Verhoeff, PIN, mobile, IFSC, dates;
Aadhaar/PAN/bank encrypted with Fernet) -> form filler fills PDFs (or a key-in sheet for online-only portals like FoSCoS and
Udyam) -> citizen reviews and explicitly confirms (any later edit invalidates it) -> download / e-Sign -> checklist and
reminders after the citizen says they submitted. Officer console (`/en/staff`) for stats, the rules review queue, the form
approval workflow and an audit-chain check. Security: rate limits, lockout, refresh-token rotation with reuse detection,
hash-chained audit log, PII-redacting logs, allowlisted outbound fetching, prod config validation that refuses unsafe starts.

## What is DONE (all on `main`, CI green at the time of handoff)
- **Core product:** everything in the flow above for 8 cities (Kolkata, Mumbai, Delhi, Bengaluru, Chennai, Hyderabad, Pune,
  Ahmedabad) and 112 business types (incl. hotel, gold/jewellery with BIS registration, liquor shops with each state's own excise rules, pharmacy, pet shop, clinic, hospital, school, college, coaching), a baseline fallback that
  escalates to an officer, and regulator notes (bank, insurance, pharmacy, liquor, ration shop, post office, clinic, school, transport...)
  instead of a wrong shop checklist. State-specific licences use `by_city` entries in `backend/app/kb/sourced_licences.py`, each written from that state's own official page.
  To add a business type, add a row to `backend/app/kb/business_types.py`; to add a licence, read the official document first and cite it in `docs/RULES_VERIFICATION.md`.
  Still to do: the 03.07.2026 Karnataka amendment and any later auction round, each pilot state's clinical-establishment law, current Telangana/Maharashtra liquor notifications, and state forms for school and coaching registration. 168 seeded rules, each with a
  source URL, confidence and "verify" flag. Accounts, password reset by SMTP email, change password, account page with data
  export and erase (DPDP), consent log, retention purge.
- **Digio (Aadhaar e-Sign + DigiLocker):** `backend/app/integrations/real/digio.py`, webhook `POST /webhooks/digio`
  (HMAC `X-Digio-Checksum`, duplicate suppression, optional IP allowlist), `external_requests` table (migration 0004),
  separate consent purpose `identity_providers`, signing-link / status / signed-PDF endpoints, UI in `DoneView.tsx`. 28 tests
  against a mocked Digio. Used automatically when `DIGIO_CLIENT_ID/SECRET` are set; otherwise a labelled demo mock.
  **Never run against the real Digio sandbox.** All confirmed API facts and the unknowns are in `docs/INTEGRATIONS.md`.
- **MSG91 SMS adapter** (`real/msg91.py`, Flow API, unit-tested with a mock). Never tried against live MSG91.
- **Rules work:** `make verify-sources` (now reports numeric vs qualitative claims), reviewer worksheet
  `docs/RULES_REVIEW_EXPORT.csv` (regenerate with `python scripts/export_rules_for_review.py docs/RULES_REVIEW_EXPORT.csv`),
  log of what was checked on official pages in `docs/RULES_VERIFICATION.md` (Udyam free, GST s.22 thresholds, GHMC Hyderabad
  trade licence page and fee table, Ahmedabad AMC shops & establishments page). Official URLs for FSSAI/FoSCoS, Udyam, GST and
  most state shops-and-establishments and municipal trade pages are in `backend/app/kb/catalog.py` and the allowlist in
  `backend/config/sources.yaml`.
- **Legal pages:** `/[locale]/privacy` and `/[locale]/terms` in en/hi/bn, linked in the footer, with live retention period,
  hosting region and grievance contact from `GET /privacy/policy`. They show a "draft, pending legal review" banner until
  `NEXT_PUBLIC_LEGAL_REVIEWED=true`.
- **Deployment files:** `render.yaml` (API + worker + Postgres + Redis), `docs/DEPLOYMENT_VERCEL_RENDER.md`,
  `docker-compose.prod.yml` + Caddy for a VPS alternative, `backend/scripts/create_admin.py` (first officer; inside the image
  at `/app/scripts/create_admin.py`). `DATABASE_URL` from Render is converted to asyncpg automatically.
- **Verified:** backend lint/types/tests/evals, frontend lint/typecheck/unit/build, 4 Playwright e2e tests, compose smoke,
  container scan, pip-audit/npm audit/bandit/gitleaks, accessibility DOM audit of the main pages.

## What is LEFT (your work, in this order; skip nothing)
### A. Production deployment (the human logs in and holds the secrets; you guide, check and fix)
Follow the numbered owner steps in `docs/LAUNCH_CHECKLIST.md` section 6 and `docs/DEPLOYMENT_VERCEL_RENDER.md`. After the
human says it is live: check `https://<api>/ready`, a real signup/login, a full business session, password-reset email,
reminders, create the first officer, confirm database backups and an uptime monitor, run the load test in `docs/LOAD_TEST.md`
and fix what it finds. Render has no India region (Singapore); if the department needs in-India storage, move the backend to
an Indian cloud and update `DATA_REGION` and the privacy text. Size the Render plans for real traffic.
### B. Digio sandbox then production
Needs the human to obtain sandbox credentials. Then run the sandbox checklist in `docs/INTEGRATIONS.md`, fix any request-shape
differences, and **implement the DigiLocker result mapping from a real response** (name, address, Aadhaar/PAN fields into answer
keys with `source="document"`, encrypted where sensitive). It is deliberately not guessed today. Only then production
credentials and the production webhook IPs (`13.126.198.236`, `52.66.66.81`).
### C. MSG91 SMS
After the human completes DLT approval, put `MSG91_AUTHKEY` and `MSG91_TEMPLATE_ID` in Render, send a real test SMS to the
human's own number, and fix the adapter if the live request shape differs (DLT errors 203/211 mean sender/template not approved).
### D. Rules verification (most important for trust)
Replace placeholder source pages with exact fee/timeline pages and fill gaps only from official sources, never from memory:
fire-safety NOC and pollution-board (CTE/CTO) pages for Maharashtra, Delhi, Karnataka, Tamil Nadu, Telangana, Gujarat;
trade-licence fee schedules for Pune, Ahmedabad, Mumbai, Delhi, Bengaluru, Chennai, Kolkata; shops-and-establishments fees and
timelines per state; GST fee, timeline and current per-state threshold; FSSAI 2026 fee slabs and validity; a cited source for
every timeline. Several government sites block bots or firewall automated fetches: read them in a real browser (read-only),
and if still unreadable ask the human to paste the page. With `ANTHROPIC_API_KEY`/`ANTHROPIC_MODEL` set and `DEMO_MODE=false`,
`POST /admin/refresh` extracts grounded claims (the quote must appear on the page). A reviewer then marks each rule
verified/corrected/rejected in the officer console. Re-export `docs/RULES_REVIEW_EXPORT.csv` after changes.
### E. Official forms
The 3 bundled PDFs are watermarked placeholders. After the human gets FSSAI's permission, officers fetch Form A and Form B
through the officer console (allowlisted URLs: Form A `https://foscos.fssai.gov.in/assets/docs/registrationForm_A.pdf`, Form B
state `https://foscos.fssai.gov.in/assets/docs/stateForm_b.pdf`, Form B central
`https://fcstraining.fssai.gov.in/assets/docs/centralForm_b.pdf`), you write the field-map JSON in
`backend/app/forms/templates/`, and an officer approves it. FSSAI and Udyam registration are online-only, so keep the key-in
sheet there. Other departments need their own written permission. See `docs/INTEGRATIONS.md` for the field-map procedure.
### F. Launch hardening
Counsel review of privacy/terms/DPDP consent text, then set `NEXT_PUBLIC_LEGAL_REVIEWED=true` on Vercel. Native-speaker review of
Hindi and Bengali copy (especially the `legal` and `done.esign*` strings). Real-phone testing on a slow network, with voice
input, and a screen-reader pass. Security: penetration test or at least the `docs/SECURITY.md` checklist, secrets-rotation plan,
a backup-restore test, move browser tokens from `sessionStorage` to httpOnly cookies behind a BFF, consider MFA/OIDC, design
the CSC-operator delegation model, decide LLM egress/residency with counsel. Pilot with 5-10 real shop owners
(`docs/PILOT_PLAN.md`), collect feedback, fix, then launch.
### G. Business readiness (ask the owner; these are decisions, not code)
Who pays and how (free for citizens and funded by a department/CSC programme, subscriptions, per-use)? Support channel and
response times, an incident/on-call contact (`docs/RUNBOOK.md`), a monthly cost estimate (Render plans, Postgres, SMTP, MSG91 per
SMS, Digio per signature and DigiLocker call, LLM usage), a custom domain, sender-domain SPF/DKIM/DMARC, and a data-processing
agreement with each provider. Not built and optional: WhatsApp and UMANG adapters (mocked today), CSC-operator delegation.
Write the answers into `docs/`, wire any configuration they imply, and put the cost table in the final report.

## What ONLY THE HUMAN can do (ask for each one; give exact click-by-click steps; wait for "done")
Never do these yourself and never ask the human to paste a secret into chat: they put values into Render/Vercel/`.env.prod`.
1. **MSG91 (SMS):** complete KYC, register on a telecom operator's TRAI DLT portal (Airtel, Vi, BSNL, STPL or Tata) as an entity,
   register a 6-character sender ID (header) of their choice and the template `Red Tape Navigator reminder: {#var#}`
   (service-implicit/transactional, ONE variable), link them in MSG91 (Sender Id and Templates pages), create a MSG91 Flow from the
   template, then copy the Template ID and Auth Key into Render. Ask them to tell you when approved so you can test a real SMS.
2. **Digio:** submit the "Get in Touch" form at https://www.digio.in with the official business email (it has a reCAPTCHA; if the
   form errors, retry from another network or email Digio directly) asking for sandbox (UAT) client id/secret, DigiLocker via
   DigiStudio with template `DIGILOCKER_AADHAAR_PAN`, Aadhaar eSign enabled, and production onboarding requirements. Credentials
   go into Render, never chat. They also set the webhook URL `https://<api>/webhooks/digio` and secret in Digio's enterprise
   dashboard (Profile > Webhooks).
3. **Deployment logins and secrets:** generate `SECRET_KEY` and `FIELD_ENCRYPTION_KEY` (`make keygen`) on their machine and
   BACK UP the encryption key (losing it destroys stored Aadhaar/PAN answers); create an SMTP account with a verified sender
   domain (SES, Brevo, SendGrid or NIC mail); sign in to Render (New > Blueprint > this repo > `render.yaml`) and Vercel (Add New
   Project > Root Directory `frontend` > `NEXT_PUBLIC_API_URL`); fill the `sync:false` env vars; set `CORS_ORIGINS` and
   `WEB_BASE_URL` to the Vercel https origin; create the first officer in the Render shell with
   `ADMIN_PASSWORD='...' python /app/scripts/create_admin.py officer@their-domain admin`; enable Postgres backups and an uptime
   monitor on `/ready`.
4. **FSSAI:** email `helpdesk-foscos@fssai.gov.in` asking permission to reproduce Form A and Form B; the reply is the proof.
   Tell you when they answer.
5. **Counsel and reviewers:** legal review of the privacy and terms text; native Hindi and Bengali review; rule sign-off in the
   officer console using `docs/RULES_REVIEW_EXPORT.csv`.
6. **Set a real `GRIEVANCE_CONTACT`** (the DPDP grievance officer shown to citizens). Production refuses to start without it.
7. **Business decisions** in section G, and a real-phone/slow-network test plus the 5-10 shop-owner pilot.
8. **Optional:** an Anthropic API key (`ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`) for the live rules refresh. It costs API usage.

## Gotchas learned the hard way
- Several Indian government sites reset connections or block non-browser clients (GST portal, some municipal sites). This does
  not mean a rule is wrong. Read them in a real browser, read-only; never bypass a firewall or CAPTCHA.
- Digio's API docs are JavaScript-rendered; the content is in a shadow DOM. Use a real browser and read it through the shadow roots.
- Digio production webhook IPs: the FAQ lists `13.126.198.236`; the environments page also lists `52.66.66.81`. The IP allowlist
  only works behind a trusted proxy and uses the first `X-Forwarded-For` hop, which can be forged: the HMAC checksum is the real control.
- A login error "Could not sign in. Check your details." is the UI's generic text for ANY failed auth call, including a server 500
  (for example an outdated local database). Check the API response before blaming credentials.
- Windows: for multi-line Python edits, write a script file and run it; quoted heredocs break in some shells.
- The e2e suite uses ports 3000 and 8000 and reuses a server already on them only if it answers `/ready` (this app). Another
  project on port 8000 used to make every e2e sign-up fail; stop it first.
- CI cancels in-progress runs when you push again; the gitleaks step needs full history (`fetch-depth: 0`, already set).
- Docker is not always running locally; the compose stack is verified by the CI `compose-smoke` job.

## Definition of done (all must be true before you stop)
All tests, lint, types, evals, e2e and CI green; production live on HTTPS with real SMTP, MSG91 and Digio (production credentials,
sandbox-tested first); core rules verified by a reviewer and every other rule still labelled "verify with the authority"; official
forms loaded with permission where available; privacy/terms approved and the draft banner off; no demo labels visible in
production (`DEMO_MODE=false`); backups, uptime monitoring, load test and security checklist done; pilot feedback addressed;
README and docs updated; `docs/LAUNCH_CHECKLIST.md` fully resolved; everything committed and pushed to `main`; and a final written
report listing what is live, what is simulated, what remains, and the monthly running costs.

## First message to the human (send this when you start)
Confirm you have repo access and CI is green, then list the eight items under "What ONLY THE HUMAN can do", ask which they have
already done, and start immediately on everything that does not depend on them (sections D, F and the code parts of B and C).
