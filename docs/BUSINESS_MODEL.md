# Business model (draft, all prices and numbers are placeholders)

Status: DRAFT for the owner. Nothing here is a market study. Every number is an assumption unless a source is cited.

## Who it is for
1. Individuals and first-time shop owners (one business): need to know what to apply for, in what order.
2. Owners with several outlets: need a calendar of renewals across outlets.
3. Professionals (CAs, consultants, lawyers, CSC operators): manage many clients and want one place for each client's plan, documents and renewals.

## Plans (prices live in `backend/config/pricing.yaml`, placeholders)
| Plan | For | Limits | Placeholder price |
|---|---|---|---|
| Free | trying it, one business | 1 business, 5 vault documents, email reminders | Rs 0 |
| Plus | one serious business | form pre-fill, SMS reminders, vault, calendar export, city comparison | Rs 199/month or 1,999/year |
| Multi-outlet | up to 10 businesses | everything in Plus plus bulk calendar | Rs 599/month or 5,999/year |
| Partner | professionals, up to 100 clients | client workspaces, white-label, referrals | Rs 1,499/month or 14,999/year |

The plan, the checklist and the cited rules stay free: they are the public-good part and the reason people trust the product. Payment is for convenience features (pre-filled forms, reminders by SMS, storage, many businesses).

## What is built (test mode only)
Done 2026-11-10: plans from `pricing.yaml`, `GET /billing/plans|me|invoices`, `POST /billing/checkout|cancel`, a Razorpay hosted-link adapter and signed idempotent webhook, gap-free invoice numbers with GST split, grace period after a plan lapses, admin refund record, and a server-side paywall on the prefilled-form download (402 `upgrade_required`). Still to build: invoice PDF, billing page and customer portal in the web app, plan-limit enforcement (businesses, team members, vault), teams, partner portal.
Plan/entitlement model, payment-provider abstraction (Razorpay test mode first), signed webhooks with idempotency, GST invoice records, server-side entitlement checks. No real money moves until the owner supplies live provider keys and company details (see `docs/OWNER_ACTIONS.md`).

## Costs the product itself carries (see docs/FINAL_REPORT.md when written)
Hosting and Postgres, email, SMS per message (MSG91), Digio per signature and DigiLocker call, optional LLM usage, payment gateway fees. All are the owner's contracts; amounts depend on the owner's quotes and are not asserted here.

## Unit economics
Not estimated. Needs real conversion and cost data from the pilot (docs/PILOT_PLAN.md). Assumption to test: a small share of free users convert to Plus, and partners bring several clients each.

## Alternatives the owner may prefer
Free for citizens and funded by a department or CSC programme (then billing stays off: set `BILLING_ENABLED=false`).
