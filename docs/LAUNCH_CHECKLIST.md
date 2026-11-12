# Launch checklist

Status key: DONE / WAITING ON OWNER / BLOCKED ON THIRD PARTY. Updated as work proceeds.

## 1. Health check: DONE (2026-11-08)
- Backend: 114 tests pass, coverage 95.8%, ruff clean.
- Frontend: lint, typecheck, unit tests (5) and production build pass.
- Local run (SQLite, production web build): `/ready` ok, 185 rules loaded, `/en` `/hi` `/bn` `/en/staff` return 200.
- Signup, login, `/auth/me` and wrong-password rejection (401) verified.

## 2. Digio (DigiLocker + Aadhaar eSign): WAITING ON OWNER, then BLOCKED ON THIRD PARTY
- [ ] Owner: request sandbox credentials from Digio (see docs/INTEGRATIONS.md). A request is drafted in the owner's Gmail (2026-11-12): add Digio's address or paste it into their contact form, fill the bracketed parts, send.
- [ ] Digio: creates DigiStudio template `DIGILOCKER_AADHAAR_PAN`, enables eSign, issues UAT client id/secret.
- [x] Me: remaining Digio docs read; interfaces redesigned; adapters, webhook (checksum/IP/duplicates), consent step, UI, 28 mocked-HTTP tests done.
- [ ] Me, after credentials: run the sandbox checklist in docs/INTEGRATIONS.md, implement DigiLocker field mapping from a real response.
- [!] Digio website contact form returned an error on 2026-11-08; retry or email Digio directly.

## 3. MSG91 SMS: WAITING ON OWNER
- [ ] Sign up, KYC, TRAI DLT sender + template, Flow, auth key. Then live test SMS.

## 4. FSSAI forms: WAITING ON OWNER to send the request, then BLOCKED ON THIRD PARTY (FSSAI permission reply)
- [ ] A permission request to `helpdesk-foscos@fssai.gov.in` is drafted in the owner's Gmail (2026-11-12). Fill the bracketed parts and send.

## 5. Rules verification: partly done; reviewer sign-off WAITING ON OWNER/officer
- [x] `make verify-sources` run; metric made meaningful (numeric vs qualitative). Log: docs/RULES_VERIFICATION.md.
- [x] Checked on official pages: Udyam free, GST s.22 thresholds, GHMC trade page, AMC shops page. Catalogue URLs/wording updated.
- [x] Reviewer worksheet exported: docs/RULES_REVIEW_EXPORT.csv (168 rules, all UNVERIFIED).
- [x] 2026-11-10: Pune and Bengaluru trade-licence fee pages not readable (no fee on PMC site; BBMP page will not load); logged in docs/RULES_VERIFICATION.md.
- [ ] Waiting on a reviewer/department: GST/FSSAI fee slabs, fire NOC and pollution pages outside West Bengal, trade-licence fee schedules, timelines.
- [ ] Waiting on owner: set ANTHROPIC_API_KEY/MODEL and run POST /admin/refresh if wanted (costs API usage).

## 6. Deployment: IN PROGRESS, WAITING ON OWNER (six values in Render)
Updated 2026-11-12. **State on 2026-11-12:** the owner has Render and Vercel accounts (both signed in with GitHub). Render read `render.yaml` without errors. The Blueprint has **not** been applied yet: it is waiting for six values only the owner can type. Nothing is live. Whether the Brevo (email sender) account exists is not confirmed.
Step-by-step list with the current status of each step: `docs/OWNER_ACTIONS.md` part A. Guide: `docs/DEPLOY_NOW.md`.

Done:
- [x] `render.yaml` rewritten as a zero-cost trial (one API + PostgreSQL) against Render's current Blueprint specification; the old file used
      plan names Render no longer lists. `render.production.yaml` is the paid launch set-up (API, worker, PostgreSQL, Redis; shared environment group).
- [x] Render's Blueprint page parsed `render.yaml` and listed "Create database rtn-db" and "Create web service rtn-api" with the nine prompted values (2026-11-12).
- [x] Render generates `SECRET_KEY` and `FIELD_ENCRYPTION_KEY` (the app accepts Render's key format).
- [x] Scheduled jobs run inside the API when `RUN_SCHEDULER=true`, so the trial needs no worker and no Redis.
- [x] First officer from `BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD` (free instances have no shell). It never overwrites an existing password.
- [x] Managed-PostgreSQL URLs with `sslmode=` (Neon, Supabase, external Render URLs) are accepted.
- [x] `scripts/verify_deploy.py <api> <web> [--journey]` checks a live deployment from outside (tried against a local stack).
- [x] Backup-and-restore drill (`scripts/backup_restore_drill.sh`) runs in CI on every push and passed.
- [x] Owner created the Render and Vercel accounts (2026-11-12).

Pending, in order:
- [ ] Owner: Brevo account with a verified sender (not confirmed).
- [ ] Owner: type `GRIEVANCE_CONTACT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `BOOTSTRAP_ADMIN_EMAIL`, `BOOTSTRAP_ADMIN_PASSWORD` into the Render
      Blueprint form and click Deploy Blueprint. **Current blocker.** A developer or assistant must not type passwords or keys.
- [ ] Note the real API address. `rtn-api.onrender.com` is taken by another Render user, so the address will carry a suffix.
- [ ] Check the first build: the Docker image has never been built on Render, and the app has never started against Render PostgreSQL
      (`CREATE EXTENSION vector`, PostgreSQL 16). Fix whatever the deploy log shows.
- [ ] Owner: copy `FIELD_ENCRYPTION_KEY` from the Render dashboard into a password manager (losing it destroys stored Aadhaar/PAN answers).
- [ ] Vercel: import the repo, Root Directory `frontend`, `NEXT_PUBLIC_API_URL` = the API address, deploy.
- [ ] Render: set `CORS_ORIGINS` and `WEB_BASE_URL` to the Vercel address (they hold `https://placeholder.example` until then).
- [ ] Run `verify_deploy.py --journey`; real sign-up; password-reset email; first-officer sign-in and `/en/staff`; delete the `BOOTSTRAP_ADMIN_*` values.
- [ ] Uptime monitor on `/ready` (also keeps the free instance awake so reminders go out).
- [ ] Before day 30 after the Blueprint is applied: upgrade the free database, or it is deleted.
- [ ] Load test against the hosted site (`docs/LOAD_TEST.md`); only the laptop baseline exists.
- [ ] Record the two live addresses in `README.md` and `docs/FINAL_REPORT.md`, and set the status there to "live".
Render has no India region (Singapore); if the department needs in-India storage, use an Indian cloud with `docker-compose.prod.yml`.

## 7. Launch hardening and pilot: partly done
- [x] Privacy policy and terms pages (en/hi/bn) at `/privacy` and `/terms`, linked in the footer; retention, region and grievance contact read live from the API.
- [x] Accessibility DOM audit of home, account, privacy, terms, reset, staff (lang, titles, one h1, labels, names, landmarks, no horizontal overflow on home): no issues found after hydration. Unique titles added for the legal pages.
- [ ] Counsel review of privacy/terms/DPDP consent text, then set `NEXT_PUBLIC_LEGAL_REVIEWED=true` (WAITING ON OWNER/counsel).
- [x] Hindi and Bengali now cover the whole product: interface strings (`frontend/messages/*.json`) AND backend text (licence names, every rule, document list, authority name, form titles and field labels, checklists, notices, reminder titles) via `backend/app/i18n_content/` (about 270 strings per language). The browser sends its language; the server translates responses. Tests fail if an English string is added without a translation.
- [ ] Native-speaker review of ALL Hindi and Bengali text, especially `backend/app/i18n_content/data_hi.py` / `data_bn.py` (legal and fee wording), `legal` and `done.esign*` strings (WAITING ON OWNER). Not translated: the officer console (English only).
- [ ] Real phone test (slow network, voice input) and screen-reader pass (WAITING ON OWNER: needs a real device).
- [x] Backup restore test: automated drill in CI (`scripts/backup_restore_drill.sh`). Threat model written (`docs/THREAT_MODEL.md`); a test walks every API route and fails if one answers without sign-in.
- [ ] Independent penetration test / security sign-off; secrets rotation drill on the hosted site (procedure in `docs/RUNBOOK.md`).
- [ ] Browser tokens are still in `sessionStorage`; moving them to httpOnly cookies needs the site and API under one domain (design in `docs/THREAT_MODEL.md`).
- [ ] Pilot with 5-10 shop owners (docs/PILOT_PLAN.md).
- [ ] Native review also of the new Help page text (`help` section of `frontend/messages/hi.json` and `bn.json`).
- [ ] Two-factor sign-in tried with a real authenticator app on a phone (only the automated browser test exists).
- [ ] Owner decisions still open: funding, operator details for the legal pages, support channel, custom domain, data-processing agreements,
      the 11 Dependabot pull requests, whether the repository stays public (`docs/OWNER_ACTIONS.md` part D).

## 7a. Development backlog (no owner input needed unless stated)
- [ ] Cookie-based sessions instead of tokens in `sessionStorage` (needs the site and API under one domain: owner buys a domain first). Design: `docs/THREAT_MODEL.md`.
- [ ] Nonce-based Content-Security-Policy so inline scripts can be disallowed.
- [ ] DigiLocker field import (needs one real sandbox response from Digio).
- [ ] Field maps for FSSAI Form A and Form B (after FSSAI's permission and an officer's fetch).
- [ ] Rule gaps listed in `README.md` section 10 and `docs/HUMAN_TODO.md` Part 2 C (official pages that would not load or are scans).
- [ ] Design for CSC-operator delegation (an operator acting for many citizens).
- [ ] Rate limiting shared across instances (only needed with more than one API instance).
- [ ] Not built from the wish list: partner portal for professionals, document vault, per-licence landing pages, support-ticket inbox,
      WhatsApp and UMANG adapters, more cities (Jaipur and Lucknow were left out because sources conflict).
- [ ] `.github/workflows/deploy.yml` is still a template with placeholder steps; Render deploys from `main` after CI passes, so it is unused.

## 8. Final docs, CI green, final report: DONE (2026-11-12)
- [x] `docs/FINAL_REPORT.md`: what is real, what is simulated, what remains and who must do it, monthly running costs.
- [x] All local gates green on 2026-11-12: 459 backend tests, evaluation set, frontend lint/types/unit/build, 12 browser tests. CI result: see the run for the final commit.
- [x] Emails drafted in the owner's Gmail (not sent): FSSAI permission request and Digio sandbox request. The owner fills the bracketed parts and sends them.

## 9. Billing: REMOVED 2026-11-10 (decision: the site is free to use and charges no one)
- [x] Billing code, pricing file and paywall deleted; migration 0006 drops the billing tables; `tests/test_free_forever.py` guards against it returning.
