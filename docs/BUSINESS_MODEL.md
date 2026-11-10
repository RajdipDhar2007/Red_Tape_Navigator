# Business model: free for everyone

Decision (owner, 2026-11-10): **Red Tape Navigator is free to use. No one is ever charged for the app or the site.**

This is enforced in code, not just stated:
- There is no payment provider, checkout, subscription, invoice or paywall in the code base, and no price list. Migration `0006` removed the billing tables that an earlier test-mode build had created.
- `backend/tests/test_free_forever.py` fails if a billing, checkout, invoice, Razorpay or subscription route, setting or table is ever added back.
- Every feature (plan, checklist, form pre-fill and download, reminders, vault, calendar) is open to every signed-in user.
- The product never collects card, UPI or bank details.

## Who it is for
1. Individuals and first-time shop owners: need to know what to apply for, in what order.
2. Owners with several outlets: need a calendar of renewals across outlets.
3. Professionals (CAs, consultants, lawyers, CSC operators): manage many clients' plans and renewals. Also free.

## Who pays for running it
The owner, or someone the owner chooses. Nothing here is decided or asserted; these are options for the owner:
- the owner's own funds
- a grant, a CSR programme or a sponsor
- a government department or CSC programme that wants it for its citizens
- volunteers and donated services

Any option that puts a price, a donation prompt or advertising in front of users is a product change and needs the owner's explicit decision first.

## Running costs (the owner's contracts; amounts are not asserted)
Hosting and Postgres, email, SMS per message (MSG91, only if SMS reminders are switched on), Digio per signature and DigiLocker call (only if e-sign is switched on), and optional LLM usage. The free product works without SMS, e-sign and the LLM (rules-first mode). See `docs/HUMAN_TODO.md` Part 4 for indicative figures.
