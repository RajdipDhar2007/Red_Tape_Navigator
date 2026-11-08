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
- [ ] Waiting on a reviewer/department: GST/FSSAI fee slabs, fire NOC and pollution pages outside West Bengal, trade-licence fee schedules, timelines.
- [ ] Waiting on owner: set ANTHROPIC_API_KEY/MODEL and run POST /admin/refresh if wanted (costs API usage).

## 6. Deployment (Render, Vercel, SMTP, first officer, backups, monitoring, load test): WAITING ON OWNER

## 7. Launch hardening and pilot: partly done
- [x] Privacy policy and terms pages (en/hi/bn) at `/privacy` and `/terms`, linked in the footer; retention, region and grievance contact read live from the API.
- [x] Accessibility DOM audit of home, account, privacy, terms, reset, staff (lang, titles, one h1, labels, names, landmarks, no horizontal overflow on home): no issues found after hydration. Unique titles added for the legal pages.
- [ ] Counsel review of privacy/terms/DPDP consent text, then set `NEXT_PUBLIC_LEGAL_REVIEWED=true` (WAITING ON OWNER/counsel).
- [ ] Native-speaker review of Hindi and Bengali copy, especially `legal` and `done.esign*` strings (WAITING ON OWNER).
- [ ] Real phone test (slow network, voice input) and screen-reader pass (WAITING ON OWNER: needs a real device).
- [ ] Penetration test / security sign-off, backup restore test, secrets rotation drill.
- [ ] Pilot with 5-10 shop owners (docs/PILOT_PLAN.md).

## 8. Final docs, CI green, final report: NOT STARTED
