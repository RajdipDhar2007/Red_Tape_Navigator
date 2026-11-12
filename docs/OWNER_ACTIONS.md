# Owner actions (the only things a developer cannot do)

Do them in this order. Never paste secrets into chat; put them in Render, Vercel or `.env.prod`.

1. Repo and CI: nothing to do (private repo, CI green).
2. Hosting, start here: `docs/DEPLOY_NOW.md` (Brevo, Render Blueprint `render.yaml`, Vercel root `frontend`; free, about 30 minutes).
3. Secrets: Render generates them; copy `FIELD_ENCRYPTION_KEY` from the Render dashboard to a password manager (losing it destroys stored Aadhaar/PAN answers).
4. Email: SMTP/SES account with a verified sender domain; SPF, DKIM, DMARC.
5. `GRIEVANCE_CONTACT`: the DPDP grievance officer shown to users (production refuses to start without it).
6. Operator name, address and support email for the legal pages (the service is free; there is no billing).
7. (Removed: the service is free and takes no payments.)
8. SMS: MSG91 KYC, TRAI DLT entity, sender ID and template `Red Tape Navigator reminder: {#var#}`, then `MSG91_AUTHKEY`, `MSG91_TEMPLATE_ID`, `MSG91_TEXT_VAR` (must equal the variable name in the template).
9. Digio: sandbox request via digio.in, then credentials and webhook secret. A request is drafted in your Gmail (fill the bracketed parts).
10. FSSAI: email helpdesk-foscos@fssai.gov.in for permission to reproduce Forms A and B. Drafted in your Gmail (fill the bracketed parts, send).
11. Counsel: review privacy, terms, refund policy, DPDP consent text; then `NEXT_PUBLIC_LEGAL_REVIEWED=true`.
12. Native Hindi and Bengali reviewers; rule sign-off in the officer console.
13. Pilot with 5-10 shop owners; real-phone and slow-network tests.
14. Business decisions: final prices, support channel and on-call contact, data-processing agreements.
