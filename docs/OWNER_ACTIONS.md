# Owner actions (the only things a developer cannot do)

Updated 2026-11-12. Do them in this order. Never paste secrets into chat; type them into Render, Vercel or `.env.prod` yourself.
Details for every step: `docs/DEPLOY_NOW.md` (deployment) and `docs/HUMAN_TODO.md` (everything else).

**State on 2026-11-12:** the owner has Render and Vercel accounts (both signed in with GitHub). Render read `render.yaml` without errors. The Blueprint has **not** been applied yet: it is waiting for six values only the owner can type. Nothing is live. Whether the Brevo (email sender) account exists is not confirmed.

## A. To get the site online (about 20 minutes left)

| # | Do this | Status |
|---|---|---|
| 1 | Create Render and Vercel accounts with GitHub | DONE 2026-11-12 |
| 2 | Create a Brevo account, verify a sender address, open SMTP & API > SMTP and note the login and SMTP key | NOT CONFIRMED |
| 3 | In Render, New > Blueprint > `Red_Tape_Navigator`. Name it `red-tape-navigator`. Type `https://placeholder.example` for `CORS_ORIGINS` and `WEB_BASE_URL`, and `smtp-relay.brevo.com` for `SMTP_HOST` | Was filled in once in the browser; retype if the tab was closed |
| 4 | In the same form type the six values below, then click **Deploy Blueprint** | **PENDING: this is the current blocker** |
| 5 | When `rtn-api` is Live, note its address (it will NOT be `rtn-api.onrender.com`: that name belongs to someone else, so Render adds a suffix) and open `<address>/ready` | PENDING |
| 6 | Copy `FIELD_ENCRYPTION_KEY` from `rtn-api` > Environment into a password manager. Losing it destroys stored Aadhaar/PAN answers | PENDING |
| 7 | Vercel: Add New > Project > import the repo, Root Directory `frontend`, env `NEXT_PUBLIC_API_URL` = the Render address, Deploy | PENDING (a developer or assistant can do this once step 5 is done) |
| 8 | Render: replace both placeholders (`CORS_ORIGINS`, `WEB_BASE_URL`) with the Vercel address | PENDING (same) |
| 9 | Run `python scripts/verify_deploy.py <api> <site> --journey`; create your own account on the site; request a password reset and check the email arrives | PENDING |
| 10 | Sign in as the first officer, open `/en/staff`, change the password, turn on two-factor, then delete `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` in Render | PENDING |
| 11 | Uptime monitor (UptimeRobot, free) on `<api>/ready` every 5 minutes | PENDING |
| 12 | **Within 30 days of step 4:** upgrade the free database (US$6 a month) or it is deleted. Put the date in your calendar | PENDING |

The six values for step 4:

| Field | What to type |
|---|---|
| `GRIEVANCE_CONTACT` | the email citizens can write to about their data (shown publicly on the site) |
| `SMTP_USERNAME` | the Brevo SMTP login |
| `SMTP_PASSWORD` | the Brevo SMTP key |
| `SMTP_FROM` | the sender address verified in Brevo |
| `BOOTSTRAP_ADMIN_EMAIL` | your email: it becomes the first officer account |
| `BOOTSTRAP_ADMIN_PASSWORD` | a new password of 12 or more characters |

## B. Emails to send (drafted in your Gmail, not sent)

| # | Do this | Status |
|---|---|---|
| 13 | FSSAI permission request to `helpdesk-foscos@fssai.gov.in`: fill `[YOUR FULL NAME]`, `[PHONE NUMBER]`, `[COLLEGE / ORGANISATION AND CITY]`, send | DRAFTED |
| 14 | Digio sandbox request: add Digio's contact address (or paste the text into the "Get in Touch" form at digio.in), fill the bracketed parts, send | DRAFTED, no recipient yet |

## C. Approvals and reviews (other people)

| # | Do this | Status |
|---|---|---|
| 15 | SMS: MSG91 KYC, TRAI DLT entity, sender ID and template `Red Tape Navigator reminder: {#var#}`; then `MSG91_AUTHKEY`, `MSG91_TEMPLATE_ID`, `MSG91_TEXT_VAR` in Render | NOT STARTED (needs business documents and a fee) |
| 16 | Digio: after they reply, put the sandbox credentials and webhook secret in Render and tell the developer | WAITING ON 14 |
| 17 | FSSAI: after they reply, an officer fetches Forms A and B in the officer console; the developer writes the field maps | WAITING ON 13 |
| 18 | A lawyer reviews the privacy, terms and consent text; then set `NEXT_PUBLIC_LEGAL_REVIEWED=true` on Vercel | NOT STARTED |
| 19 | Native Hindi and Bengali reviewers check `frontend/messages/hi.json`, `bn.json` (including the new `help` section) and `backend/app/i18n_content/data_hi.py`, `data_bn.py` | NOT STARTED |
| 20 | Someone with legal or CA knowledge signs off rules in the officer console (`docs/RULES_REVIEW_EXPORT.csv` is the worksheet) | NOT STARTED |
| 21 | Real-phone, slow-network, voice-input and screen-reader test; test two-factor with a real authenticator app | NOT STARTED |
| 22 | Independent penetration test (`docs/THREAT_MODEL.md` lists what is open) | NOT STARTED |
| 23 | Pilot with 5 to 10 shop owners (`docs/PILOT_PLAN.md`) | NOT STARTED |

## D. Decisions

| # | Decide | Status |
|---|---|---|
| 24 | Who funds the running costs (`docs/BUSINESS_MODEL.md`; about US$30 a month for a launch, `docs/FINAL_REPORT.md`) | OPEN |
| 25 | Operator name, address and support email for the legal pages; support channel and hours; an on-call contact | OPEN |
| 26 | A custom domain (also needed for a verified email domain with SPF, DKIM, DMARC, and for cookie-based login) | OPEN |
| 27 | Data-processing agreements with Render, Vercel, Brevo, and later MSG91 and Digio | OPEN |
| 28 | The 11 open Dependabot pull requests on GitHub (merge or close) and the two runs stuck in "queued" for commit `ba69bc7` (cancel) | OPEN |
| 29 | Whether the repository should stay public (it carries a proprietary licence) | OPEN |
