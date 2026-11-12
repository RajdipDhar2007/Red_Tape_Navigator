> **SUPERSEDED 2026-11-10:** the owner decided the site is free to use and charges no one. Ignore every billing, pricing, Razorpay, paywall, invoice and plan-limit item below; do not build them. See `docs/BUSINESS_MODEL.md`.

# Prompt for the next session (copy everything below the line)

---

Read README.md, docs/DEVELOPER_GUIDE.md, docs/HANDOFF_PROMPT.md (especially the session logs and pitfalls), docs/RULES_VERIFICATION.md, docs/LAUNCH_CHECKLIST.md and this file. Then do the work below without stopping to ask. I (the owner) have already authorised: push to `main` after every verified change (nothing else on GitHub: no PRs, repos, issues, settings). Work on the P: drive only.

## Goal

Red Tape Navigator must stop being a demo-ready app and become a complete, deployable product with a business model: a citizen or small-business owner can sign up, get an accurate licence plan, have forms prefilled for review, track renewals, and pay for what is worth paying for, while the owner can run it as a company (billing, support, admin, analytics, compliance, operations). Everything a developer can finish without my credentials must be finished, tested and documented. Everything that needs me must be built up to the point where I only paste a key or click one button, and listed in one file.

## Standing rules (unchanged, non-negotiable)

- Never invent legal facts. Every rule, fee, timeline or form has a source recorded in docs/RULES_VERIFICATION.md; unread or unconfirmed items stay "Verify with the authority". Human-verified rules only get confidence >= 0.9.
- Never auto-submit anything to a government portal. Never send messages or emails on anyone's behalf without the user's explicit action.
- Never type real passwords, OTPs, Aadhaar/PAN, card or bank details anywhere. Test accounts only on localhost with generated values. Never commit `.env*` (except `*.example`), `*.db`, keys or secrets. No `.github/dependabot.yml`. No State Emblem of India.
- Payments: use the payment provider's TEST mode and published test cards only. Never move real money. Never store card data (provider-hosted checkout only).
- Do not run `npm run build` while dev/start servers run. Before Playwright, kill stale `next start` and `uvicorn` processes (see HANDOFF pitfall). Use the Write tool, not long heredocs, for multi-line scripts.
- Keep README, LAUNCH_CHECKLIST, RULES_VERIFICATION and HANDOFF_PROMPT true in the same commit as the change. Run every gate (ruff, mypy, pytest with real exit codes, evals, frontend lint/tsc/vitest/build, Playwright e2e), push, then watch CI for that commit with `gh run watch` in the background and fix red runs before moving on.

## Part A: finish every pending research item (use Chrome; record every attempt, including dead ends)

If a page will not load, try: the Wayback Machine copy, the gazette PDF on the egazette/department site, the department's English and local-language pages, a different network path (mobile view, `/pdf` link), then WebSearch for the official gazette number. If still unreadable, say so in the log and leave the rule as "verify". Do not guess figures.

1. Trade-licence fees: Bengaluru (GBA / BBMP notification), Chennai (GCC council resolution of 30 July 2024, official notification), Pune (PMC), Ahmedabad (AMC), Delhi (general trade licence after the property-tax merger; confirm from MCD/NDMC).
2. Pollution consent fees: Maharashtra (current MPCB fee schedule), Delhi (DPCC), West Bengal (WBPCB).
3. Fire NOC fees and validity outside Maharashtra and Delhi: Karnataka, Tamil Nadu, Telangana, Gujarat, West Bengal.
4. Liquor: Telangana excise notification, Karnataka excise amendment of 3 July 2026, Maharashtra population band for Mumbai and Pune, West Bengal and Delhi current fee schedules.
5. Clinic and health: clinic registration laws for Tamil Nadu, Telangana, Gujarat; Gujarat health-permit rules for food premises.
6. Education and coaching: UGC / university rules, state school and coaching-centre registration (start with Rajasthan, Karnataka, Maharashtra, Delhi, West Bengal, Tamil Nadu), play school and daycare rules.
7. A cited source for every timeline (not just fees), every document list and every authority name.
8. Jaipur and Lucknow: add only if two independent official sources agree; otherwise document why not. Consider adding more cities only with the same standard (Kochi, Chandigarh, Indore, Bhopal, Patna, Guwahati, Nagpur are good candidates).
9. Re-check every rule that is older than 90 days against its source and update the "last verified" date. Add a script `scripts/rule_freshness.py` that lists rules not re-verified in 90 days and fails CI when a rule is overdue (warn first, then block).
10. For each new rule: catalog/sourced text, aligned Hindi and Bengali rows, test, RULES_VERIFICATION entry, regenerated `docs/RULES_REVIEW_EXPORT.csv`.

## Part B: turn it into a business (build all of it, test mode only)

Design the model first in `docs/BUSINESS_MODEL.md` (keep it short and honest): free tier (plan + checklist + reminders for one business), paid tiers for individuals (e.g. per-plan unlock, annual renewal tracking), a multi-business plan for owners with several outlets, and a partner / professional plan (CAs, consultants, lawyers, CSC operators managing many clients). Put prices in a single config file the owner can change; use placeholder prices clearly marked as such. Then build:

1. **Billing**: provider abstraction with Razorpay (India-first: UPI, cards, netbanking, subscriptions) in TEST mode behind a flag; Stripe optional. Hosted checkout only; webhook endpoint with signature verification, idempotency keys, replay protection; plan/entitlement model in the database; upgrade, downgrade, cancel, grace period, failed-payment retry state; GST-compliant invoice generation (PDF, sequential numbers, SAC code field, GSTIN fields left as owner-config); refunds recorded; a billing page and customer portal. Tests with the provider's sandbox payloads. Entitlement checks enforced on the server, not just hidden in the UI.
2. **Accounts and teams**: email verification, password reset, session management and device list, optional TOTP 2FA, account deletion and data export (DPDP Act rights), multi-user workspaces with roles (owner, editor, viewer), and invitations.
3. **Partner / professional portal**: one login, many client workspaces, client invitation flow, bulk renewal calendar, white-label basics (name, logo, colours), per-client notes, referral links and commission tracking records (no real payouts).
4. **Admin console** (role-gated): users, workspaces, subscriptions, rule review queue (the existing review flow), rule freshness, audit log viewer, feature flags, announcement banners, content edit for FAQs, impersonation with consent and audit trail, support-ticket inbox.
5. **Support and engagement**: in-app help centre and FAQ (en/hi/bn), contact form with rate limit and spam protection, ticket model, transactional email templates (welcome, verification, reminder, receipt, renewal notice) rendered from templates with a console/log mail backend and an SMTP/SES adapter ready for keys; reminder preferences (email, SMS via the MSG91 adapter, WhatsApp as a link share only); in-app notification centre.
6. **Growth**: SEO (per-licence and per-city landing pages generated from the rule data, sitemap.xml, robots.txt, structured data, OpenGraph images, canonical and hreflang for en/hi/bn), a public "What licences do I need for <business> in <city>" page set that links to the interview, shareable result pages with no personal data, referral programme, PWA (installable, offline checklist, push opt-in), and privacy-friendly analytics (self-hosted or cookieless; no third-party trackers without consent).
7. **Product depth**: renewal calendar with .ics export; document vault (encrypted upload, expiry dates, scan type/size limits, virus-scan hook); fee calculator; "what if I move city" comparison; saved drafts of forms; form pre-fill coverage for the most common forms with a clear "review before you submit" step and the official portal deep link; offline-friendly mobile layout; voice input for the interview in Hindi and Bengali where the browser supports it; accessibility to WCAG 2.2 AA (axe in Playwright, keyboard-only pass, screen-reader labels, contrast); add more Indian languages only with a native-speaker review path (Tamil, Telugu, Marathi, Gujarati, Kannada) built as a drop-in translation pack.
8. **Compliance pack** (draft text for counsel to approve, clearly marked draft): privacy policy, terms, refund and cancellation policy, cookie notice, DPDP Act consent records and withdrawal flow, data-retention and deletion jobs, grievance officer page, a disclaimer that this is guidance not legal advice, and a rules-accuracy statement that shows the last-verified date per rule.
9. **Security hardening**: rate limits per route and per user, CSRF review, strict CSP and security headers, secrets via env only, dependency and container scans in CI (already there; keep green), audit log for sensitive actions, encryption of stored documents and PII fields at rest, backup and restore script with a tested restore, threat model in `docs/THREAT_MODEL.md`, and a short pentest checklist run against localhost.
10. **Reliability and operations**: Postgres as the production database (migrations tested up and down), Redis for rate limits and queues if needed, background jobs for reminders and emails with retries and dead-letter handling, health and readiness endpoints, structured logs with request ids, error tracking hook (Sentry-compatible DSN env, off by default), metrics endpoint, load test (Locust or k6) with a recorded baseline in `docs/PERFORMANCE.md`, graceful degradation when MSG91, Digio, the LLM or payment provider is down, and an incident runbook.
11. **Deployment kit**: production Dockerfiles, docker-compose for a single VM, Kubernetes manifests or a Helm chart, Terraform or equivalent for one cloud (pick the cheapest sensible: a single small VM plus managed Postgres), CI/CD that deploys on tag to a staging environment, environment matrix (dev/staging/prod), zero-downtime migration notes, TLS and domain steps, CDN notes, and `docs/DEPLOY.md` that a non-expert can follow. Include a cost estimate table for 100, 1,000 and 10,000 monthly users.
12. **Business documents**: `docs/BUSINESS_MODEL.md` (pricing, unit economics with stated assumptions, customer segments, channels, partner model), `docs/GO_TO_MARKET.md`, `docs/OWNER_ACTIONS.md` (the single list of things only I can do, in order, with exact fields to fill), and a one-page investor/judge summary. Do not invent market numbers; label every assumption as an assumption.

## Part C: quality bar before you call anything done

- All gates green locally and in CI for the final commit; backend coverage stays >= 80% (aim to keep ~95%); add tests for every new module; add e2e tests for sign-up -> plan -> upgrade (test mode) -> invoice -> cancel, the partner flow, the admin review flow, and the language switch.
- Run the whole app in Chrome yourself as a new user in each language and as a partner; check the console for errors; fix what you find.
- Keep the UX delightful: animations respect reduced motion, no layout jank, fast first load (record Lighthouse numbers for the home page and the checklist page in docs/PERFORMANCE.md).
- Update the README feature list and counts, the known-gaps paragraph, and docs/LAUNCH_CHECKLIST.md so they are exactly true.

## Part D: finish

Write `docs/FINAL_REPORT.md` plus a short chat summary: what is live and verified, what is simulated (and exactly what real credential or decision turns each simulation real), what remains only for the owner (deployment, Digio/MSG91/Razorpay/SES keys and DLT, FSSAI form permission, counsel and native-speaker sign-off, GRIEVANCE_CONTACT, GSTIN and company details, business registration, pilot, real-device tests), monthly running-cost estimates, and the known rule gaps with the reason for each. If anything could not be done, say so plainly. Work through the parts in order, commit and push in small verified steps, and keep going until A to D are done.
