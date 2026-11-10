# Launch checklist

Status key: DONE / WAITING ON OWNER / BLOCKED ON THIRD PARTY. Updated as work proceeds.

## 1. Health check: DONE (2026-11-08)
- Backend: 114 tests pass, coverage 95.8%, ruff clean.
- Frontend: lint, typecheck, unit tests (5) and production build pass.
- Local run (SQLite, production web build): `/ready` ok, 185 rules loaded, `/en` `/hi` `/bn` `/en/staff` return 200.
- Signup, login, `/auth/me` and wrong-password rejection (401) verified.

## 2. Digio (DigiLocker + Aadhaar eSign): WAITING ON OWNER, then BLOCKED ON THIRD PARTY
- [ ] Owner: request sandbox credentials from Digio (see steps in chat / docs/INTEGRATIONS.md).
- [ ] Digio: creates DigiStudio template `DIGILOCKER_AADHAAR_PAN`, enables eSign, issues UAT client id/secret.
- [x] Me: remaining Digio docs read; interfaces redesigned; adapters, webhook (checksum/IP/duplicates), consent step, UI, 28 mocked-HTTP tests done.
- [ ] Me, after credentials: run the sandbox checklist in docs/INTEGRATIONS.md, implement DigiLocker field mapping from a real response.
- [!] Digio website contact form returned an error on 2026-11-08; retry or email Digio directly.

## 3. MSG91 SMS: WAITING ON OWNER
- [ ] Sign up, KYC, TRAI DLT sender + template, Flow, auth key. Then live test SMS.

## 4. FSSAI forms: BLOCKED ON THIRD PARTY (FSSAI permission reply)

## 5. Rules verification: partly done; reviewer sign-off WAITING ON OWNER/officer
- [x] `make verify-sources` run; metric made meaningful (numeric vs qualitative). Log: docs/RULES_VERIFICATION.md.
- [x] Checked on official pages: Udyam free, GST s.22 thresholds, GHMC trade page, AMC shops page. Catalogue URLs/wording updated.
- [x] Reviewer worksheet exported: docs/RULES_REVIEW_EXPORT.csv (168 rules, all UNVERIFIED).
- [x] 2026-11-10: Pune and Bengaluru trade-licence fee pages not readable (no fee on PMC site; BBMP page will not load); logged in docs/RULES_VERIFICATION.md.
- [ ] Waiting on a reviewer/department: GST/FSSAI fee slabs, fire NOC and pollution pages outside West Bengal, trade-licence fee schedules, timelines.
- [ ] Waiting on owner: set ANTHROPIC_API_KEY/MODEL and run POST /admin/refresh if wanted (costs API usage).

## 6. Deployment (Render, Vercel, SMTP, first officer, backups, monitoring, load test): WAITING ON OWNER
Code and config are ready (`render.yaml`, `docs/DEPLOYMENT_VERCEL_RENDER.md`; `create_admin.py` is now inside the image).
Only the owner can do the logins and secrets. In order:
1. Generate secrets on your machine (never commit/paste): `python -c "import secrets;print(secrets.token_urlsafe(48))"` for `SECRET_KEY`;
   `make keygen` for `FIELD_ENCRYPTION_KEY`. Back up the encryption key somewhere safe: losing it destroys stored Aadhaar/PAN answers.
2. SMTP: create an account with a provider that can verify your sender domain (SES, Brevo, SendGrid or NIC mail) and note host/user/password.
3. Render: sign in (GitHub login is fine) > New > Blueprint > pick this repo and `render.yaml`. Fill the `sync:false` values on `rtn-api`
   and `rtn-worker` (same values): `FIELD_ENCRYPTION_KEY`, `CORS_ORIGINS`/`WEB_BASE_URL` (fill after step 4), `GRIEVANCE_CONTACT`, `SMTP_*`,
   and later `MSG91_*`, `DIGIO_*`. Render has no India region (Singapore); if the department needs in-India storage, use an Indian cloud.
4. Vercel: sign in with GitHub > Add New Project > this repo > Root Directory `frontend` > env `NEXT_PUBLIC_API_URL=https://<render-api-url>` > Deploy.
   Then put that Vercel https origin into Render `CORS_ORIGINS` and `WEB_BASE_URL` and redeploy the API.
5. Check `https://<api>/ready`. Create the first officer in the Render shell of `rtn-api`:
   `ADMIN_PASSWORD='<12+ chars>' python /app/scripts/create_admin.py officer@yourdomain admin` (type the password only there).
6. Turn on Render Postgres backups, add an uptime monitor on `/ready` (UptimeRobot/Better Stack, free tier is fine), optional Sentry DSN.
7. Tell me when it is live: I will run the real-signup, business-session, password-reset email and reminder checks, then the load test in `docs/LOAD_TEST.md`.

## 7. Launch hardening and pilot: partly done
- [x] Privacy policy and terms pages (en/hi/bn) at `/privacy` and `/terms`, linked in the footer; retention, region and grievance contact read live from the API.
- [x] Accessibility DOM audit of home, account, privacy, terms, reset, staff (lang, titles, one h1, labels, names, landmarks, no horizontal overflow on home): no issues found after hydration. Unique titles added for the legal pages.
- [ ] Counsel review of privacy/terms/DPDP consent text, then set `NEXT_PUBLIC_LEGAL_REVIEWED=true` (WAITING ON OWNER/counsel).
- [x] Hindi and Bengali now cover the whole product: interface strings (`frontend/messages/*.json`) AND backend text (licence names, every rule, document list, authority name, form titles and field labels, checklists, notices, reminder titles) via `backend/app/i18n_content/` (about 270 strings per language). The browser sends its language; the server translates responses. Tests fail if an English string is added without a translation.
- [ ] Native-speaker review of ALL Hindi and Bengali text, especially `backend/app/i18n_content/data_hi.py` / `data_bn.py` (legal and fee wording), `legal` and `done.esign*` strings (WAITING ON OWNER). Not translated: the officer console (English only).
- [ ] Real phone test (slow network, voice input) and screen-reader pass (WAITING ON OWNER: needs a real device).
- [ ] Penetration test / security sign-off, backup restore test, secrets rotation drill.
- [ ] Pilot with 5-10 shop owners (docs/PILOT_PLAN.md).

## 8. Final docs, CI green, final report: NOT STARTED

## 9. Billing: REMOVED 2026-11-10 (decision: the site is free to use and charges no one)
- [x] Billing code, pricing file and paywall deleted; migration 0006 drops the billing tables; `tests/test_free_forever.py` guards against it returning.
