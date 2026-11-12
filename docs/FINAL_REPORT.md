# Final report (2026-11-12)

Where the product stands, what is real, what is simulated, what is left and what it costs to run.

## 1. In one paragraph

Red Tape Navigator is built, tested and ready to deploy. It is **not live yet**. **State on 2026-11-12:** the owner has Render and Vercel accounts (both signed in with GitHub). Render read `render.yaml` without errors. The Blueprint has **not** been applied yet: it is waiting for six values only the owner can type. Nothing is live. Whether the Brevo (email sender) account exists is not confirmed. The ordered list of what is left, with the status of each step, is `docs/OWNER_ACTIONS.md`. Everything a developer can do without those values is done. The remaining items need a person or an organisation outside the code: accounts, regulatory approvals (SMS, e-sign), FSSAI's permission, a lawyer, native-language reviewers, an officer to sign off rules, and a pilot with real shop owners.

## 2. What is real and tested

| Area | State |
|---|---|
| Sign-up, login, lockout, password reset, email confirmation, two-factor sign-in, teams | Built and tested |
| Goal intake, licence plan with cited sources, interview, validation, encrypted Aadhaar/PAN, form filling, review step, downloads, key-in sheets, submission checklist | Built and tested |
| Reminders (email), **calendar file (.ics) of reminders (new)** | Built and tested |
| Officer console: review queue, form approval, statistics, audit-chain check | Built and tested |
| Privacy: consent records, export, erase, automatic deletion after the retention period | Built and tested |
| English, Hindi and Bengali for the whole interface and all rule text | Built and tested for completeness; wording not yet reviewed by native speakers |
| 9 cities, 120 business types, 16 licences, 438 rules from official sources | Seeded; every rule shows "verify with the authority" until an officer signs it off |
| Production safety checks at start-up | Built and tested: refuses dev secrets, SQLite, http origins, demo mode, missing email settings |
| **One-file hosting set-up (new)**: `render.yaml` (free trial) and `render.production.yaml` (launch) | Written against Render's current Blueprint specification; unit-tested for typos and committed secrets; **not yet applied on a real Render account** |
| **Scheduled jobs without a separate worker (new)** (`RUN_SCHEDULER=true`) | Built and tested |
| **First officer account from environment variables (new)**, for hosts without a shell | Built and tested; can never overwrite an existing password |
| **Live-deployment checker (new)**: `scripts/verify_deploy.py` | Written; run it against the real site after deploying |
| **Backup-and-restore drill (new)**: `scripts/backup_restore_drill.sh` | Runs in CI on every push against PostgreSQL |
| **Search-engine and install basics (new)**: `robots.txt`, `sitemap.xml`, web-app manifest, icon, language alternates, social preview tags | Built and browser-tested; private pages are excluded from search engines |
| **Help page (new)**: nine common questions at `/help`, in all three languages | Built and browser-tested |
| Quality gates | Backend: lint, types, 459 tests (about 96% coverage), evaluation set with zero invented facts. Frontend: lint, types, unit tests, production build, 12 browser tests. 7 CI jobs |

## 3. What is simulated or switched off

| Feature | Today | What makes it real |
|---|---|---|
| Aadhaar e-Sign and DigiLocker (Digio) | Code written and tested against a mocked Digio only. Off in production until credentials are set | Digio sandbox credentials (a request is drafted in the owner's Gmail), then the sandbox checklist in `docs/INTEGRATIONS.md`. DigiLocker field import is deliberately not written until a real response is seen |
| SMS reminders (MSG91) | Code written and unit-tested; never sent | TRAI DLT registration and MSG91 KYC by the owner (needs business documents and a fee) |
| WhatsApp, UMANG | Labelled mock only | A provider contract; no adapter is written |
| Official PDFs (FSSAI Form A/B, trade licence, Udyam) | Watermarked placeholders plus key-in sheets | FSSAI's written permission (request drafted in the owner's Gmail), then an officer fetches and approves each form in the console |
| Live rules refresh with an AI model | Off (`LLM_PROVIDER=none` on the trial) | A Gemini key or a local Ollama model; the product works without it |
| Legal pages | Shown with a "draft, pending legal review" banner | A lawyer's approval, then `NEXT_PUBLIC_LEGAL_REVIEWED=true` |

## 4. What remains, and who must do it

| # | Item | Who | How |
|---|---|---|---|
| 1 | Finish the deployment: Render and Vercel accounts exist; type six values into the Render Blueprint form and click Deploy; then Vercel import and connecting the two | Owner for the six values, then owner or developer | `docs/OWNER_ACTIONS.md` part A, steps 2 to 8 |
| 2 | Copy `FIELD_ENCRYPTION_KEY` from Render into a password manager | Owner | Step 2.5 of the same guide |
| 3 | Run `scripts/verify_deploy.py --journey` on the live site, test reset email | Owner or developer | One command |
| 4 | Uptime monitor on `/ready` | Owner | UptimeRobot, 3 minutes |
| 5 | Before day 30: upgrade the free database or move to the launch Blueprint | Owner | Needs a card |
| 6 | Send the two drafted emails (FSSAI permission, Digio sandbox) after filling the bracketed parts | Owner | Gmail, Drafts |
| 7 | MSG91 KYC and TRAI DLT registration | Owner | `docs/HUMAN_TODO.md` Part 1 item 8 |
| 8 | Lawyer reviews privacy, terms and consent text | Lawyer | Then switch the banner off |
| 9 | Native Hindi and Bengali review | Two reviewers | Files listed in `docs/LAUNCH_CHECKLIST.md` section 7 |
| 10 | Officer signs off rules in the console | Someone with legal or CA knowledge | `docs/RULES_REVIEW_EXPORT.csv` is the worksheet |
| 11 | Real-phone, slow-network, voice-input and screen-reader test | Owner | Needs devices |
| 12 | Independent penetration test | Tester | `docs/THREAT_MODEL.md` lists what is open |
| 13 | Pilot with 5 to 10 shop owners | Owner | `docs/PILOT_PLAN.md` |
| 14 | Decisions: who funds running costs, support channel, on-call contact, custom domain | Owner | `docs/BUSINESS_MODEL.md` |
| 15 | First build on Render has never run: watch the deploy log and fix what it shows | Developer | Render dashboard, `rtn-api`, Logs |
| 16 | Delete the `BOOTSTRAP_ADMIN_*` values after the first officer sign-in; two-factor on the hosting accounts | Owner | `docs/DEPLOY_NOW.md` step 6 |
| 17 | GitHub housekeeping: 11 Dependabot pull requests, two stuck runs, public or private repository | Owner | `docs/OWNER_ACTIONS.md` part D |

Development work that is still open, in order of value:

1. Keep browser tokens out of script reach (cookie-based sessions). Needs the site and API under one domain; design in `docs/THREAT_MODEL.md`.
2. Rule gaps listed in `README.md` section 10 (pages that would not load or exist only as scans). Each needs the official text.
3. DigiLocker field import, after the first real sandbox response.
4. Nonce-based Content-Security-Policy; operator-delegation design; shared rate limiting for more than one instance.
5. Not built from the earlier wish list: a partner portal for professionals, a document vault, per-licence landing pages, a support-ticket inbox. None blocks a launch. The full backlog is `docs/LAUNCH_CHECKLIST.md` section 7a.

## 5. Monthly running costs

Render figures were read from <https://render.com/pricing> on 2026-11-12. Others are marked.

| Item | Trial | Launch | Source |
|---|---|---|---|
| API (Render web service) | US$0 (`free`, sleeps when idle) | US$7 (`0.5c-512mb`) | Render pricing page |
| Worker (Render) | not used | US$7 (`0.5c-512mb`) | Render pricing page |
| PostgreSQL (Render) | US$0 (`free`, **expires after 30 days**) | US$6 (`0.1c-256mb`) + US$0.30 per GB stored | Render pricing page |
| Redis (Render Key Value) | not used | US$10 (`256mb`) | Render pricing page |
| Website (Vercel) | US$0 (Hobby, non-commercial use) | US$20 per member (Pro), if the Hobby terms do not fit | Vercel pricing, as recorded in `docs/HUMAN_TODO.md`; not re-read today |
| Email (Brevo) | US$0 (free plan, daily cap) | free plan or a paid plan by volume | Not verified today: confirm on Brevo's pricing page |
| Uptime monitor | US$0 | US$0 | UptimeRobot free plan; not verified today |
| **Total, fixed** | **US$0** | **about US$30 a month** (about US$50 with Vercel Pro) | |
| SMS (MSG91) | off | per message, plus a one-time DLT fee of roughly Rs 5,900 | Secondary sources only; confirm before paying |
| e-Sign and DigiLocker (Digio) | off | per signature and per call | Not known: ask Digio (in the drafted email) |
| Domain name | none | yearly fee | Not checked |
| AI model for rules refresh | off | free tier of Gemini or a local model | Optional |

A smaller launch is possible: keep `RUN_SCHEDULER=true` and one API instance, drop the worker and Redis, and pay about US$13 a month (API + database). Use the worker and Redis when you run more than one API instance.

## 6. What was verified, and what was not

Verified on 2026-11-12 on a development machine: every backend and frontend gate listed in section 2, including the browser tests against a production build. The CI run for the final commit is the record of the PostgreSQL, container and backup-drill jobs.

Not verified, and not claimed: any behaviour on Render or Vercel; a real email delivery; a real SMS; a real e-signature; load beyond the laptop baseline in `docs/LOAD_TEST.md`; the correctness of Hindi and Bengali wording; the legal sufficiency of the privacy and terms text; any rule beyond what its cited source says.
