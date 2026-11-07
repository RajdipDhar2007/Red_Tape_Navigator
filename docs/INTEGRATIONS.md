# Integrations and going live

All external services sit behind small interfaces in `backend/app/integrations/interfaces.py` with a **labelled mock**
(`mock.py`) and a **real-implementation stub** (`real/`). `INTEGRATIONS_MODE=mock` (default) uses the mocks;
`real` selects the stubs, which raise `NotImplementedError` until you complete onboarding and implement them.

**No interface has a "submit" method.** e-Sign signs a document the citizen already reviewed; DigiLocker only reads
documents the citizen authorises; messaging only notifies. A test fails the build if a submission capability appears.

> The onboarding requirements below are what is typically needed. Programmes, forms and fees change: confirm current
> requirements with each issuing body before planning timelines.

## 1. DigiLocker (document fetch)

| | |
|---|---|
| Interface | `DigiLocker.list_documents`, `fetch_document` |
| Mock | Returns clearly fake values labelled "Demo mode: simulated DigiLocker"; imports never overwrite what the user typed |
| What you need to go live | Registration as a requester/partner (via API Setu / DigiLocker partner onboarding), sandbox then production credentials (client id/secret), an OAuth2 consent redirect so the **citizen** authorises each fetch, a signed agreement and a published privacy notice |
| Implement | `real/digilocker.py`: OAuth2 code flow, fetch issued documents (Aadhaar/PAN XML or PDF), verify signatures where provided, map to answer keys with `source="document"` (the report then shows "document (DigiLocker)") |
| Data handling | Treat fetched Aadhaar data as sensitive: encrypt, never log, minimise, honour DigiLocker/UIDAI storage rules |

## 2. Aadhaar e-Sign

| | |
|---|---|
| Interface | `ESign.request_signature(document_sha256, signer_ref)` |
| Mock | Returns `SIMULATED-NOT-LEGALLY-VALID`, `legally_valid: false`, label "Demo mode: simulated e-Sign". The UI repeats the label |
| What you need to go live | Typically: an agreement with an e-Sign Service Provider (ESP) approved under the IT Act's e-Sign framework, ASP registration with that ESP, Aadhaar authentication licensing (AUA/Sub-AUA) arranged through the ESP, UIDAI/CCA compliance, a signing-page redirect and callback, and counsel's approval of the user-consent text |
| Implement | `real/esign.py`: send the hash of the **reviewed** PDF, redirect the citizen to the ESP's OTP page, receive the signed PDF/PKCS#7, store it, audit the event |
| Rule | Only callable after the explicit review consent (the API enforces `review_required`) |

## 3. UMANG

`UMANG.list_services(query)`. Mock returns a labelled demo entry. Going live requires department onboarding through the
UMANG programme owner (NeGD/MeitY) and API credentials. Use it to deep-link citizens to the right service rather than to
replicate it.

## 4. WhatsApp Business, SMS, email (follow-up reminders)

| Channel | Needs |
|---|---|
| WhatsApp | WhatsApp Business Platform account (directly or via a BSP), verified business, **pre-approved message templates**, recorded user opt-in (we log the `reminders` consent) |
| SMS | Sender ID and **DLT registration** with templates (TRAI rules) via an SMS gateway |
| Email | Verified sender domain (SPF, DKIM, DMARC), SES/SMTP credentials |

`Messenger.send(to, text)` is implemented by `MockMessenger` (records to an outbox, labelled "not actually sent") and
`RealMessenger` (stub). Reminders are only sent while the `reminders` consent is active.

## 5. Government portals (FoSCoS, Udyam, GST, municipal portals)

* We **read** public pages only, from the allowlisted domains in `backend/config/sources.yaml`, honouring robots.txt and
  rate limits.
* We **never** log in, solve captchas, or submit on a citizen's behalf. A captcha/login wall raises
  `HumanHandoffRequired`; the checklist then instructs the citizen to complete the step on the portal.
* Do not scrape behind logins. If a department offers an API or data-sharing MoU (e.g. via API Setu), implement it as a
  new adapter, not as a scraper.
* For production use of a portal's data at scale, get the department's written permission.

## How to add a real form (replace a placeholder)

1. Put the official fillable PDF in `backend/app/forms/templates/<form_id>.pdf` (replace the placeholder).
2. List its AcroForm field names:
   `python -c "import pymupdf,sys; [print(w.field_name, w.field_type_string) for p in pymupdf.open(sys.argv[1]) for w in p.widgets()]" form.pdf`
3. Edit `<form_id>.json`: set `"placeholder": false`; for each PDF field add
   `{"pdf_field": "<exact name>", "label": "...", "source": "<interview key>", "transform": "upper|title|rupees|date_ddmmyyyy|checkbox_if:<value>|digits_spaced", "required": true, "max_len": N}`.
   Use `"sources": [...]` for composites. Leave signature fields with no `source` (never auto-filled). Set `"confirm": true`
   where the mapping is a judgement call so the user is asked to confirm.
4. If the form needs data the interview doesn't ask yet, add a `FieldDef` to `backend/app/interview/fields.py`
   (question text in en/bn/hi + validator).
5. **Flat (non-fillable) PDF?** Set `"kind": "flat"` and give each field `x`, `y`, `page`, `size` (points from bottom-left);
   the reportlab overlay fills it.
6. Run `pytest backend/tests/test_forms.py` and `make eval`. The registry refuses unknown transforms or source keys at load.
7. Link the form to a licence by setting `"form": "<form_id>"` in `backend/app/kb/catalog.py`.
8. Legal check: confirm you may redistribute the form and that its current version is used.

## How to add a licence, city or source

* **Licence / activity / city:** edit `backend/app/kb/catalog.py` (the seed pack), then `make eval` and extend
  `backend/evals/golden_cases.json`.
* **Source domain:** add to `backend/config/sources.yaml`. Only official government domains; prefer the narrowest host.
* **Replace seed claims with verified ones:** run live verification (`POST /admin/refresh`, or the weekly job) with
  `ANTHROPIC_API_KEY` + `ANTHROPIC_MODEL` set; extracted claims need a verbatim quote from the official page. Low
  confidence items land in the human review queue (`/admin/review-queue`).

## Go-live checklist (summary)

| Item | Owner |
|---|---|
| DigiLocker partner approval + credentials | Programme / legal |
| ESP agreement + ASP onboarding for e-Sign | Programme / legal |
| WhatsApp templates, DLT registration, email domain | Operations |
| Written permission/MoU with the pilot municipality for data use | Programme |
| Real form PDFs + legal check of redistribution | Product |
| Verified rules pack (human-reviewed) for the pilot scope | Domain expert |
| Security audit and penetration test; DPIA; grievance officer | Security / legal |
| India-region hosting and data-flow review (incl. LLM egress) | Platform / legal |
