# Owner actions (the only things a developer cannot do)

Do them in this order. Never paste secrets into chat; put them in Render, Vercel or `.env.prod`.

1. Repo and CI: nothing to do (private repo, CI green).
2. Secrets: `make keygen`; back up `FIELD_ENCRYPTION_KEY` (losing it destroys stored Aadhaar/PAN answers).
3. Hosting: Render Blueprint (`render.yaml`) and Vercel (root `frontend`); steps in `docs/DEPLOYMENT_VERCEL_RENDER.md`.
4. Email: SMTP/SES account with a verified sender domain; SPF, DKIM, DMARC.
5. `GRIEVANCE_CONTACT`: the DPDP grievance officer shown to users (production refuses to start without it).
6. Company details for invoices: legal name, address, GSTIN, SAC code, invoice prefix (to be read from env; billing stays off until set).
7. Payments: Razorpay account KYC, then test keys first (`RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`); live keys only after a test-mode run you have watched.
8. SMS: MSG91 KYC, TRAI DLT entity, sender ID and template `Red Tape Navigator reminder: {#var#}`, then `MSG91_AUTHKEY`, `MSG91_TEMPLATE_ID`, `MSG91_TEXT_VAR` (must equal the variable name in the template).
9. Digio: sandbox request via digio.in, then credentials and webhook secret.
10. FSSAI: email helpdesk-foscos@fssai.gov.in for permission to reproduce Forms A and B.
11. Counsel: review privacy, terms, refund policy, DPDP consent text; then `NEXT_PUBLIC_LEGAL_REVIEWED=true`.
12. Native Hindi and Bengali reviewers; rule sign-off in the officer console.
13. Pilot with 5-10 shop owners; real-phone and slow-network tests.
14. Business decisions: final prices, support channel and on-call contact, data-processing agreements.
