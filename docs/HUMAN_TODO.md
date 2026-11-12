# What the human must do, and what to give the developer (Claude)

Last updated 2026-11-12. This is the background and detail. **The ordered list with the current status of every step is `docs/OWNER_ACTIONS.md`.**

**State on 2026-11-12:** the owner has Render and Vercel accounts (both signed in with GitHub). Render read `render.yaml` without errors. The Blueprint has **not** been applied yet: it is waiting for six values only the owner can type. Nothing is live. Whether the Brevo (email sender) account exists is not confirmed. Next step: `docs/OWNER_ACTIONS.md` part A, step 4.

**Rules for everything below**
- Never paste passwords, OTPs, card or bank details, Aadhaar or PAN into chat. Secrets go into Render, Vercel or `.env.prod` yourself.
- Developers (and Claude) cannot create accounts, pass CAPTCHAs, accept terms, complete KYC or move money. Those are yours.
- The service is free. No payment provider is used or needed.

---

## Part 1. Things only you can do (accounts, legal, money)

| # | What | Why it blocks launch | How you know it is done |
|---|------|----------------------|--------------------------|
| 1 | Keys: Render now generates them. After the Blueprint is applied, copy `FIELD_ENCRYPTION_KEY` from the Render dashboard to two safe places. (`make keygen` is only for the Docker Compose route.) | Losing it makes stored Aadhaar/PAN answers unreadable. | Key saved offline. |
| 2 | Hosting: follow `docs/DEPLOY_NOW.md` (free trial: Brevo, Render via `render.yaml`, Vercel root `frontend`; about 30 minutes, no card). Launch set-up: `render.production.yaml`, `docs/DEPLOYMENT_VERCEL_RENDER.md`. | Accounts exist (2026-11-12); the Blueprint is not applied yet (six values pending). | A public HTTPS URL loads `/en`. |
| 3 | A domain name, pointed at Vercel and Render. | Needed for email, SEO and cookies. | `https://yourdomain` works. |
| 4 | Email sending: SMTP or SES account, verified sender domain, SPF, DKIM, DMARC. | Reminders, verification and support mail. | A test mail reaches a Gmail inbox, not spam. |
| 5 | Grievance officer name and email for the DPDP notice, as `GRIEVANCE_CONTACT`. | Production refuses to start without it. | App starts in prod mode. |
| 6 | Support email and the legal entity or person who runs the service (shown on the legal pages). No GST registration is needed just to offer a free service; ask your accountant if you ever receive money. | Legal pages need a named operator. | Pages show the name. |
| 8 | MSG91 SMS: KYC, TRAI DLT entity, sender ID, template `Red Tape Navigator reminder: {#var#}`. Then `MSG91_AUTHKEY`, `MSG91_TEMPLATE_ID`, `MSG91_TEXT_VAR` (must equal the template variable name). | SMS reminders. Never sent live yet. | One reminder to your own phone. |
| 9 | Digio sandbox request via digio.in (eSign and DigiLocker), then credentials and webhook secret. A request is drafted in your Gmail (no recipient yet; fill the bracketed parts). | The adapter has never run against a real sandbox. | Sandbox sign flow completes. |
| 10 | FSSAI: email helpdesk-foscos@fssai.gov.in for permission to reproduce Forms A and B. Drafted in your Gmail; fill the bracketed parts and send. | Form reproduction rights. | Written reply saved. |
| 11 | A lawyer reviews privacy policy, terms, refund policy, DPDP consent text. Then set `NEXT_PUBLIC_LEGAL_REVIEWED=true`. | Pages show "draft" until then. | Banner disappears. |
| 12 | Native Hindi and Bengali speakers review the translations, including the Help page added on 2026-11-12. | Translations are machine-assisted and not reviewed. | Corrections returned. |
| 13 | Sign off rules in the officer console (a person with legal or CA knowledge). | Only human-verified rules may exceed confidence 0.9. | Rules marked verified. |
| 14 | Pilot with 5 to 10 shop owners; test on real phones and slow networks. | Not done. | Feedback collected. |
| 15 | Penetration test and a load test on the hosted site. (The backup-restore drill is automated in CI since 2026-11-12.) | Not done. | Reports filed. |
| 16 | Upgrade the free Render database within 30 days of applying the Blueprint. | It is deleted otherwise. | Plan shows `0.1c-256mb`. |
| 17 | Delete `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` in Render after the first officer sign-in; turn on two-factor on the Render, Vercel, GitHub and Brevo accounts. | Whoever holds those accounts holds everything. | Variables gone; two-factor on. |
| 18 | Decide on the 11 Dependabot pull requests, the two stuck "queued" runs for commit `ba69bc7`, and whether the repository stays public. | Housekeeping on your GitHub; a developer will not touch it without being asked. | Decided. |

---

## Part 2. Details to give me so I can finish the product

Send these in chat (no secrets). Anything you leave blank stays a labelled placeholder.

### A. Product decisions
1. **Support**: channel (email, WhatsApp, form), hours, and who answers.
2. **Product name, logo, brand colours**, and whether "Red Tape Navigator" is final. No State Emblem of India will be used.
3. **Who funds the running costs** (own funds, grant, sponsor, department). I will not add any price, donation prompt or advertising without your explicit yes.
4. **Partner (CA / consultant) features**: which free tools they need (client list, shared renewal calendar), client limits if any are needed to protect the servers.

### B. Operator and contact details (for the legal pages)
Name of the person or entity running the service, registered address, support email, grievance officer name and email.

### C. Rules research I could not finish
These pages did not load in Chrome or were scanned PDFs. Paste the text, or reply "you may download <file>" and I will read it locally.
- **Delhi DPCC consent fee table**: `dpcc.delhi.gov.in/sites/default/files/inline-files/fee_structure.pdf`
- **Pune trade-licence fee** (PMC)
- **Bengaluru trade-licence fee** (BBMP)
- **Ahmedabad trade-licence fee** (AMC)
- **Delhi general trade licence fee and process**
- **West Bengal pollution board fee circular** (on `wbocmms.nic.in`)
- **Chennai GCC trade-licence notification**
- Anything else you know of: fire NOC fees outside Maharashtra and Delhi, liquor rules, clinic laws (Tamil Nadu, Telangana, Gujarat), coaching and school registration.

Every rule I add needs a source link or pasted official text. Without one it stays "Verify with the authority".

### D. Scope choices
- **Cities to add** beyond the current set (Jaipur and Lucknow are undecided).
- **Languages**: stay at English, Hindi, Bengali, or add more.
- **Which Part B features first.** The order I would use: accounts and teams, partner portal, admin console, support, SEO and PWA, then the security and deployment kits.

### E. Access I need for testing
- Permission each time for anything on GitHub other than pushing to `main`.
- Permission to download specific files (I ask with filename, source and size).

---

## Part 3. What is already built, and what is not

**To try yourself:** sign up, open Your account, turn on two-factor with an authenticator app on your phone, then create a team. Tell me anything that feels wrong; a real phone has not been tried yet.

**Built and tested:** rules catalogue (438 rules, English, Hindi, Bengali), freshness check in CI, interview and form prefill, migrations to `0007`, email confirmation, two-factor sign-in (authenticator app) and teams with invitation links. **There is no billing: the site is free to use and charges no one** (an earlier test-mode billing build was removed on 2026-11-10).

**Built on 2026-11-12:** calendar export of reminders, robots/sitemap/manifest, threat model, one-file hosting set-up with a 30-minute guide, live-deployment checker, backup drill, final report (`docs/FINAL_REPORT.md`).

**Not built yet:** partner portal, document vault, per-licence landing pages, support-ticket inbox. None blocks a launch. (A help page with common questions exists at `/help`.)

**Never done and not claimed:** live SMS, live eSign, native-speaker review, legal review, pentest, load test, a pilot.

---

## Part 4. Documents to have ready, and what each step costs

Checked 2026-11-10 from web searches. Most figures come from vendor blogs and comparison sites, not the official pages, so treat them as estimates. Confirm each on the official page before paying. "Not checked" means I did not look it up and will not guess.

| Step | Documents to have ready | Fee |
|------|-------------------------|-----|
| TRAI DLT (needed before any SMS) | Business PAN, proof of business (registration certificate), authorised person's ID and mobile, a letter of authorisation for the sender. Exact list varies by operator. Not checked on an official page. | About Rs 5,900 including GST, one time, on the first operator portal (Jio is best supported). Sources disagree on BSNL and Vi. Airtel not found. Later portals are said to be free. |
| MSG91 account and SMS credits | Not checked. Usually your DLT entity ID, sender ID and approved template. | Not checked. |
| Hosting: Render | GitHub access. A card only for the paid plans. | Trial: US$0 (`render.yaml`; the free database is deleted after 30 days). Launch: API US$7, worker US$7, Postgres US$6 plus US$0.30 per GB, Key Value US$10, about US$30 a month (read from render.com/pricing on 2026-11-12). Details: `docs/FINAL_REPORT.md`. |
| Hosting: Vercel | Card for billing. | Pro is about US$20 per user per month, including a usage credit. The free Hobby plan is not meant for commercial use; check Vercel's terms. |
| Domain name | Not checked. | Not checked. |
| Digio sandbox and production | Not checked. Request it through digio.in. | Not checked. |
| FSSAI form reproduction | An email to helpdesk-foscos@fssai.gov.in stating the purpose. | Not checked. |
| Lawyer review (privacy, terms, refund, DPDP consent) | Draft pages from the app, your business details. | Set by the lawyer. Get a quote. |
| Penetration test | A staging URL and written permission. | Set by the tester. Get a quote. |

If you meant the licence documents and fees that the app shows to its users (FSSAI, trade licence, fire and so on), those are already stored per rule and city in `backend/app/kb/catalog.py`. `docs/RULES_REVIEW_EXPORT.csv` lists the documents and fee text for all 438 rules in one sheet. Tell me if you want them added to this file instead.

Sources: [DLT fee guide](https://crm.smsgatewayhub.com/knowledge-base/article/dlt-registration-charges-cost-breakdown-in-india), [Render pricing](https://render.com/pricing.md), [Vercel Pro plan](https://vercel.com/docs/plans/pro-plan).
