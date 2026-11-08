# Go-live checklist (what is built, what only you can do)

The software is feature-complete for the citizen journey, officer oversight and production operation. Four things
cannot be completed from inside the repository because they need third parties or domain sign-off. Each has a
tool or switch ready so the work is data entry and configuration, not development.

| # | Item | Status in code | What is still needed | Owner |
|---|---|---|---|---|
| 1 | **Password reset / email** | **Done.** Single-use 30-minute links, signs out all sessions, change-password, SMTP adapter, localised mails, anti-enumeration | Set `SMTP_*` and `WEB_BASE_URL` (a prod start refuses without them) | IT |
| 2 | **Rules data** | Curated seed pack with live-verification pipeline (`make verify-sources`; live LLM refresh with `ANTHROPIC_API_KEY`), review queue + officer console to sign off each rule | Departments verify each rule. **Measured on 2026-11-08 from a developer machine: 1 of 168 seeded rules had its numbers on the cited page, because the seed cites portal home pages, and 9 of 20 sources did not respond to the bot.** Treat every rule as "verify with the authority" until resolved in the review queue | Legal / dept. SMEs |
| 3 | **Official forms** | **Form fetching is built**: officers fetch the official PDF from an allowlisted department URL, the platform checks it fits the field map, an officer approves it, weekly re-checks flag changes (see [INTEGRATIONS](INTEGRATIONS.md)) | Supply the official PDF URL for each form and write its field map (a form whose AcroForm names differ from ours cannot be approved until the map is updated). Get the authority's permission to reproduce. Note: FSSAI and Udyam registration are completed **online** on FoSCoS / Udyam; there is no authoritative paper PDF to fill, so for those the recommended next feature is a "ready-to-key-in" answer sheet (not built yet) | Dept. + product |
| 4 | **DigiLocker, Aadhaar e-Sign, UMANG, WhatsApp/SMS** | Interfaces, mocks (clearly labelled in the UI), consent and audit hooks. Email is real. | Partner onboarding and credentials from each provider (API Setu / NeGD / ESP / WhatsApp BSP, TRAI DLT). These are administrative approvals, not code | Programme / legal |

## How to verify the rules pack

```bash
make verify-sources        # fetches every cited URL through the guarded fetcher and reports which claims'
                           # numbers appear on the live page (never edits or marks anything verified)
```

Then, with `ANTHROPIC_API_KEY` + `ANTHROPIC_MODEL` set and `DEMO_MODE=false`, an admin runs `POST /admin/refresh` to
extract grounded claims (quote must appear in the page) from the live pages. Low-confidence or changed rules land in the
officer console review queue; an officer marks each *verified / corrected / rejected* with a note, which is audited.
Replace the home-page URLs in `backend/app/kb/catalog.py` with the exact fee/timeline pages the department confirms.

## Why we do not ship invented "official" forms

A form that looks official but is not would mislead citizens and embarrass the department. The three bundled PDFs are
watermarked placeholders by design, and the review screen says so.
