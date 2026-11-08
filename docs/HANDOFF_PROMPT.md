# Handoff prompt for Claude Code (paste everything below into Claude Code)

You are taking over "Red Tape Navigator", an AI assistant that helps Indian citizens and small businesses (shops, bakeries,
salons, small manufacturing, online sellers) work out which licences they need, interviews them for the missing details,
fills official forms, and tracks follow-ups. Goal: make it a finished, production-ready business product.

## Rules for you (the assistant)
- Commit and push to `main` automatically after every verified change (tests and lint green). No pull requests, no new
  repos, no other GitHub actions unless the owner asks. Never commit `.env*` files (except the `*.example` ones), `*.db`,
  or secrets.
- Never type passwords, API secrets, Aadhaar/PAN, or OTPs into any website, and never create accounts or solve CAPTCHAs for
  the owner. Those steps are the human's. Tell them exactly what to click, then continue once they confirm.
- Never invent legal facts (fees, timelines, rules) or API behaviour. If official docs cannot be read, ask the human to paste
  them. Never present unverified rules as official; every rule stays flagged "verify with the authority" until an officer
  signs it off.
- Do not auto-submit anything to a government portal (CAPTCHA/OTP/Aadhaar login and terms forbid it). The product fills
  official PDFs and gives a "key-in sheet" for online-only portals; the citizen submits.
- Do not use the State Emblem of India (illegal under the 2005 Act). The tricolour + wheel mark is original; an authorised
  department may supply its emblem via `NEXT_PUBLIC_EMBLEM_URL`.

## Step 0: get the code and run it
1. Ask the owner (GitHub user RajdipDhar2007) to add you as a collaborator on the PRIVATE repo, or to give you access.
2. `git clone https://github.com/RajdipDhar2007/Red_Tape_Navigator.git && cd Red_Tape_Navigator`
3. Read `README.md`, `docs/GO_LIVE.md`, `docs/DEPLOYMENT_VERCEL_RENDER.md`, `docs/INTEGRATIONS.md`, `docs/ASSUMPTIONS.md`.
4. Backend (Python 3.12 or 3.13): `cd backend && python -m venv .venv`, activate it, `pip install -e ".[dev]"`, then
   `python -m pytest -q` (expect about 114 passing, coverage over 80%) and `ruff check app tests`.
5. Frontend (Node 20+): `cd frontend && npm ci && npm run lint && npm run typecheck && npm test && npm run build`.
6. Run locally without Docker: from `backend`, set `DATABASE_URL=sqlite+aiosqlite:///./dev_local.db`, run
   `alembic upgrade head`, `python -m app.kb.seed_loader`, then `uvicorn app.main:app --port 8000`.
   From `frontend`: `npm run dev` (http://localhost:3000). Backend CORS defaults to port 3000 only.
   WARNING: never run `npm run build` while `npm run dev` is running; they share `.next` and the dev server breaks (500s).
   Stop dev servers first. Kill stray `node` dev servers if ports 3001+ appear.

## What is already built (all on `main`)
- Backend (FastAPI): auth with password rules, lockout, refresh tokens, password reset by email (SMTP); consent (DPDP);
  intake that understands the business type and city (8 cities: Kolkata, Mumbai, Delhi, Bengaluru, Chennai, Hyderabad, Pune,
  Ahmedabad; many business types plus a baseline fallback that escalates to an officer); research/rules knowledge base
  (168 seeded claims with source URLs and confidence); interview engine with field validation and encrypted
  Aadhaar/PAN/bank answers; form filler for PDFs plus an official-form fetch/approval workflow; "key-in sheet" for online-only
  portals (FSSAI FoSCoS, Udyam); checklist and reminders (worker); officer console and admin stats; privacy/erase
  endpoints; prod config validation that refuses an unsafe start; audit log, metrics, rate limits.
- Frontend (Next.js 15, i18n English/Hindi/Bengali): redesigned UI (tricolour logo, icons, saffron/navy/green palette),
  home with sign-up/login, session flow (goal, interview, review, done), account/password page, staff console, reset page.
  A hydration bug on the account page was fixed.
- Deployment files: `render.yaml` (API + worker + Postgres + Redis on Render), `docs/DEPLOYMENT_VERCEL_RENDER.md`,
  `docker-compose.prod.yml` + Caddy for a VPS alternative. `DATABASE_URL` from Render is auto-converted to asyncpg.
- MSG91 SMS adapter (`backend/app/integrations/real/msg91.py`): uses the Flow API (`POST https://control.msg91.com/api/v5/flow`,
  `authkey` header). Unit-tested with a mock; NOT yet tested against live MSG91.
- Official URLs added for FSSAI/FoSCoS, Udyam, GST, shops-and-establishments (WB, Maharashtra, Delhi, Telangana, Gujarat,
  Karnataka eKarmika, Tamil Nadu), trade licences (Kolkata, Mumbai, Delhi, Bengaluru, Chennai, Hyderabad, Pune), and matching
  allowlist domains. FSSAI fee shown as "changed in 2026, confirm on FoSCoS". No other fee/timeline figures were changed.
- Verified: backend tests/lint pass; frontend lint, typecheck, unit tests, production build pass; `npm audit` and `pip-audit`
  clean; production frontend serves all routes with CSP/HSTS headers; signup and login work in a real browser.

## What is NOT done (your job, in this order)
### A. Production deployment (human logs in; you guide and verify)
1. Generate secrets locally (never commit): `SECRET_KEY` = `python -c "import secrets;print(secrets.token_urlsafe(48))"`,
   `FIELD_ENCRYPTION_KEY` = `make keygen` (Fernet). BACK UP the encryption key; losing it destroys stored Aadhaar/PAN answers.
2. Backend on Render: the human signs in at render.com (GitHub login is fine), chooses New > Blueprint, picks this repo and
   `render.yaml`, and fills the `sync:false` env vars (same values on `rtn-api` and `rtn-worker`): FIELD_ENCRYPTION_KEY,
   CORS_ORIGINS and WEB_BASE_URL (= the Vercel https origin), GRIEVANCE_CONTACT, SMTP_*, MSG91_*. Render has no India region
   (Singapore is used and DATA_REGION says so); if the department needs in-India data, move the backend to an Indian cloud.
3. SMTP: use a provider with a verified sender domain (SES, SendGrid, Brevo, or NIC mail). Human creates the account and
   gives the SMTP host/user/password directly into Render's dashboard, not in chat.
4. Frontend on Vercel: human signs in at vercel.com with GitHub, Add New Project, import the repo, Root Directory `frontend`,
   env var `NEXT_PUBLIC_API_URL=https://<render-api-url>`, deploy. Then set that Vercel domain into the backend CORS_ORIGINS
   and WEB_BASE_URL and redeploy the backend. Add a custom domain if the business has one.
5. Check `https://<api>/ready` shows ready and a real signup/login works end to end. Create the first officer with
   `scripts/create_admin.py` (it is not inside the Docker image; run it from a Render shell after copying it, or add it to the
   backend image and document that).
6. Add uptime monitoring, Sentry DSN (optional), database backups on Render, and run the load test in `docs/LOAD_TEST.md`.

### B. Digio (DigiLocker + Aadhaar eSign) — blocked on the owner's account
- Human fills the "Get in Touch" form at https://www.digio.in (official business email required, reCAPTCHA) or emails Digio
  sales/support, asking for: sandbox (UAT) client id/secret, DigiLocker via DigiStudio with template
  `DIGILOCKER_AADHAAR_PAN`, Aadhaar eSign enabled, and production onboarding requirements. If the website form errors, use
  another browser/network or the contact details on digio.in. Credentials go into Render env vars / `.env.prod` by the human.
- Confirmed from docs.digio.in (public docs; use a real browser, the pages are JavaScript-rendered):
  Auth is HTTP Basic (client id:secret). Base URLs: sandbox `https://ext.digio.in:444`, production `https://api.digio.in`.
  Webhook source IPs: sandbox 35.154.20.28; production 13.126.198.236 and 52.66.66.81.
  DigiLocker: `POST {BASE}/client/kyc/v2/request/with_template` (JSON: customer_identifier required, customer_name,
  template_name, reference_id, transaction_id, notify_customer, expire_in_days, generate_access_token). Status:
  `POST {BASE}/client/kyc/v2/{id}/response` (statuses requested, approval_pending, approved, rejected, failed, expired,
  skipped). The citizen completes consent in Digio's flow, then results arrive by webhook or status call.
  eSign: `POST {BASE}/v2/client/document/upload` (multipart `file` PDF + `request` JSON: file_name, signers, expire_in_days,
  display_on_page, notify_signers, will_self_sign, callback, sign_coordinates); a JSON variant takes base64 `file_data`.
- Still to read in the docs (as the human, in a browser): webhook payloads, download-media, eSign status/download, error codes.
- Then: redesign the interfaces in `backend/app/integrations/interfaces.py` (today `ESign` only takes a hash and `DigiLocker`
  assumes direct fetch; Digio needs "upload PDF, get signing link" and "start request, wait for consent, receive result"),
  write `real/digio_*.py` adapters, webhook endpoint with signature/IP checks, UI steps, tests with mocked HTTP, and run them
  against the sandbox before any production use. Keep the labelled mock when credentials are missing.

### C. MSG91 SMS
- Human signs up at msg91.com, completes KYC, registers on TRAI DLT (sender/header and a template with ONE variable, e.g.
  "Red Tape Navigator reminder: ##var1##"), creates a MSG91 Flow using that template, and gives you `MSG91_AUTHKEY` and
  `MSG91_TEMPLATE_ID` (put in Render env, not chat). Send a test SMS to the human's own number and confirm; fix the adapter
  if the live request shape differs (DLT errors 203/211 mean sender/template not approved).

### D. Rules verification (most important for trust)
- Run `make verify-sources` and then, with `ANTHROPIC_API_KEY` + `ANTHROPIC_MODEL` set and DEMO_MODE=false, `POST /admin/refresh`
  as an admin to extract grounded claims. A lawyer or department reviewer marks each rule verified/corrected/rejected in the
  officer console (`/en/staff`). Earlier measurement: only 1 of 168 seeded rules had its numbers on the cited page. Replace
  portal home-page URLs in `backend/app/kb/catalog.py` with the exact fee/timeline pages. Still unconfirmed: fire-safety and
  pollution sources outside West Bengal, and Hyderabad/Pune/Ahmedabad fee pages. Do not guess figures.

### E. Official forms
- The 3 bundled PDFs are watermarked placeholders. The human emails helpdesk-foscos@fssai.gov.in asking permission to
  reproduce FSSAI Form A / Form B (a draft was prepared in Gmail); the reply is the proof of permission. Official PDFs:
  Form A https://foscos.fssai.gov.in/assets/docs/registrationForm_A.pdf, Form B (state)
  https://foscos.fssai.gov.in/assets/docs/stateForm_b.pdf, Form B (central) https://fcstraining.fssai.gov.in/assets/docs/centralForm_b.pdf
  (training subdomain; prefer a FoSCoS-hosted copy). After permission: officers fetch each PDF through the officer console
  (allowlisted URLs only), you write the field map JSON in `backend/app/forms/templates/`, and an officer approves it. Other
  departments need their own permission; FSSAI and Udyam registration themselves are online-only, so keep using the key-in sheet.

### F. Product and compliance hardening before launch
- Privacy policy and terms pages, grievance officer contact (`GRIEVANCE_CONTACT`), DPDP consent text review by counsel,
  data retention/erase check, cookie/storage review.
- Accessibility pass (keyboard, contrast, screen reader) and Hindi/Bengali copy review by native speakers.
- Real-device test on a phone, slow network, and voice input; fix any layout issue.
- Security: third-party penetration test or at least `docs/SECURITY.md` checklist, secrets rotation plan, backups restore test.
- Pilot with 5-10 real shop owners (`docs/PILOT_PLAN.md`), collect feedback, fix, then launch.

## Definition of done
All tests/lint/build green in CI; production deploy live on HTTPS with real SMTP and (if approved) MSG91 and Digio; at least
the core rules verified by a reviewer; official forms loaded with permission; no demo labels visible in production; docs updated;
everything committed and pushed to `main`.
