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
| Interface | `DigiLocker.start_request`, `get_status` (consent happens on the provider's page; see the Digio section) |
| Mock | Returns clearly fake values labelled "Demo mode: simulated DigiLocker"; imports never overwrite what the user typed |
| What you need to go live | Registration as a requester/partner (via API Setu / DigiLocker partner onboarding), sandbox then production credentials (client id/secret), an OAuth2 consent redirect so the **citizen** authorises each fetch, a signed agreement and a published privacy notice |
| Implement | `real/digilocker.py`: OAuth2 code flow, fetch issued documents (Aadhaar/PAN XML or PDF), verify signatures where provided, map to answer keys with `source="document"` (the report then shows "document (DigiLocker)") |
| Data handling | Treat fetched Aadhaar data as sensitive: encrypt, never log, minimise, honour DigiLocker/UIDAI storage rules |

## 2. Aadhaar e-Sign

| | |
|---|---|
| Interface | `ESign.create_request(pdf, ...)`, `get_status`, `download_signed` (the citizen signs on the provider's page) |
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

## Fetching the official PDF (built)

The platform downloads the current PDF from the issuing authority instead of shipping a copy in the repository:

1. Make sure the form's field map exists (`backend/app/forms/templates/<form_id>.json`, see the next section). Optionally set
   `"official_url": "https://<allowlisted official site>/<path>.pdf"` in that JSON.
2. In the officer console (**Official forms**) or via `POST /admin/forms/<form_id>/fetch {"url": "..."}` (admin role), fetch it.
   The download goes through the same guard rails as research: HTTPS, domain allowlist (checked on every redirect),
   `robots.txt`, per-domain rate limit, 8 MB cap, PDF signature check, captcha/login pages are never bypassed.
3. The platform reports whether the PDF **fits our field map** (every required field of the map exists in the PDF; missing and
   unmapped fields are listed). An officer can view the PDF, then **Approve and use** it. An incompatible PDF cannot be approved.
4. From then on citizens' review, preview and download use the approved copy, the placeholder banner disappears for that form,
   and the review screen shows where it came from (site, date, fingerprint).
5. The weekly worker job re-fetches every form with a known URL. A changed file becomes a new *candidate* plus an officer review
   item; **citizens keep getting the previously approved copy until an officer approves the new one.**

Limits: only fillable (AcroForm) PDFs can be checked automatically; scanned or flat PDFs, and forms that are filled online
(FoSCoS, Udyam), need their field map built by hand. The platform never guesses an official URL: it must be supplied.

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

## SMS via MSG91 (implemented)

`app/integrations/real/msg91.py` sends reminders through MSG91's Flow API (`POST /api/v5/flow`, `authkey` header).
Set `MSG91_AUTHKEY` and `MSG91_TEMPLATE_ID`; the factory then uses it for the `sms` channel in any mode.
Indian SMS needs a TRAI DLT-approved template, so create one with a single variable and link it to a MSG91 flow.
Verify against your MSG91 account in test mode before go-live (DLT errors 203/211 mean sender/template not approved).
Docs check 2026-11-10 (docs.msg91.com/sms/send-sms, updated 29 Oct 2026): URL, headers, body and success response match the adapter. The docs' example names the variable `VAR1`; the key must equal the variable name in your DLT template exactly, so set `MSG91_TEXT_VAR` accordingly.
Status: request shape is unit-tested against a mock transport; it has NOT been exercised against live MSG91 yet.

## Digio (DigiLocker KYC + Aadhaar eSign): implemented, sandbox-untested

Code: `app/integrations/real/digio.py` (adapters), `app/api/webhooks.py` (`POST /webhooks/digio`), session endpoints in
`app/api/sessions.py`, table `external_requests` (migration 0004; ids and statuses only, never documents or identity data).
Digio is used whenever `DIGIO_CLIENT_ID` and `DIGIO_CLIENT_SECRET` are set (like MSG91); otherwise the labelled mock runs.
With the mock and `DEMO_MODE=false`, the e-Sign and DigiLocker endpoints answer 503 instead of pretending.

**Status: all request shapes are unit-tested against a mocked Digio (`tests/test_digio.py`). Nothing has been run against
the real Digio sandbox yet, because no credentials exist. Run the sandbox checklist below before any production use.**

### Flow

e-Sign: citizen reviews and confirms the forms -> consents to sharing with the provider (purpose `identity_providers`) ->
`POST /sessions/{sid}/esign` uploads the reviewed PDF and returns `signing_url` (Digio also emails/SMSes the signer) ->
the citizen signs on Digio's page with the Aadhaar OTP (we never see it) -> Digio calls the webhook (`doc.signed`) ->
`GET /sessions/{sid}/esign/{id}` shows `completed` (falls back to polling Digio if the webhook is late) ->
`GET /sessions/{sid}/esign/{id}/signed.pdf` fetches the signed file from Digio on demand (nothing is stored here).

DigiLocker: `POST /sessions/{sid}/documents/digilocker` creates a DigiStudio request with `notify_customer=true`; Digio
sends the citizen the consent link; the result arrives by webhook or `GET /sessions/{sid}/documents/digilocker/{id}`.

### Digio facts confirmed from documentation.digio.in (2026-11-08)

- Base URLs: sandbox `https://ext.digio.in:444`, production `https://api.digio.in`. Each environment has its own client id/secret
  and its own webhook account and secret. Auth is HTTP Basic (client id : client secret).
- Webhook source IPs (FAQ): sandbox `35.154.20.28`; production `13.126.198.236` (a second production IP `52.66.66.81` was seen on
  the environments page). Webhooks are configured in the Enterprise dashboard (sandbox `https://ext-enterprise.digio.in`,
  production `https://enterprise.digio.in`) under Profile > Webhooks, with a URL and a secret.
- Webhook authenticity: header `X-Digio-Checksum` = HMAC-SHA256 (hex) of the payload, keyed by the webhook secret.
  Envelope: `{id, created_at (epoch ms), event, entities[], payload{}}`. Delivery is at-least-once (de-duplicate by `id`).
  Digio expects HTTP 200 within 10 seconds; failures are retried and eventually pause the account's whole webhook queue, so
  an authentic delivery is always answered 200. Sandbox delay is about 5 minutes, production about 5 seconds.
- e-Sign: `POST {BASE}/v2/client/document/upload` (multipart `file` + `request` JSON text; request fields used: `file_name`,
  `signers[{identifier, reason, sign_type}]`, `expire_in_days`, `display_on_page`, `notify_signers`, `will_self_sign`,
  `callback` (idempotency key), `include_authentication_url`). Response: `id` (DID...), `agreement_status`
  (draft|requested|completed|expired|failed), `signing_parties[]` (status, `authentication_url`).
  Details: `GET {BASE}/v2/client/document/{id}`. Download: `GET {BASE}/v2/client/document/download?document_id=DID...` (PDF).
  Events: `doc.signed`, `doc.sign.failed` (`error_code`, `error_message`), `doc.sign.rejected`.
- DigiLocker via DigiStudio: `POST {BASE}/client/kyc/v2/request/with_template` (template `DIGILOCKER_AADHAAR_PAN`, created by
  Digio support), status `POST {BASE}/client/kyc/v2/{id}/response` (requested, approval_pending, approved, rejected, failed,
  expired, skipped). Events: `DOCUMENTS_PULLED_SUCCESSFULLY`, `DOCUMENTS_PULLED_PARTIALLY`, `KYC_REQUEST_APPROVED|REJECTED|
  TERMINATED|EXPIRED`; the DigiLocker payload carries `kyc_request_id`, `reference_id`, `state`, `shared_documents`.
- Error codes (Digi Sign): documented list with codes such as 1079 (invalid signer), 1108/1155 (expired), 1015 (provider
  credits exhausted), 1205 (UIDAI/ESP down), plus ESP/UIDAI codes (110-112, 300, 400, 996-998). The adapter maps the common ones
  to citizen-safe messages and never logs identifiers or response bodies.

### NOT confirmed / not implemented (do not guess)

- The exact shape of the DigiLocker result data (name, address, Aadhaar/PAN fields) in the status response and in
  download-media. `DigioDigiLocker.get_status` therefore returns `fields: {}`; nothing is auto-imported from Digio yet.
  Implement the mapping from a real sandbox response, with `source="document"`, and encrypt Aadhaar/PAN values.
- Whether `signers[]` accepts a `name` field, and the precise error body format (we read `code`/`error_code`, otherwise generic).
- Whether the same webhook secret and URL can serve both products (it is account-level, so yes in principle).

### Sandbox checklist (once credentials exist)

1. Set `DIGIO_CLIENT_ID`, `DIGIO_CLIENT_SECRET`, `DIGIO_ENV=sandbox`, `DIGIO_WEBHOOK_SECRET`, `DIGIO_WEBHOOK_IPS=35.154.20.28`
   on `rtn-api` (Render env or `.env.prod`, never in git). In the Digio sandbox dashboard set the webhook URL to
   `https://<api>/webhooks/digio` with the same secret and enable the Digi Sign and Digi Studio events.
2. Ask Digio to confirm template `DIGILOCKER_AADHAAR_PAN` exists for your account and that Aadhaar eSign is enabled.
3. Sign a reviewed form end to end; confirm `signing_url`, the webhook (check `external_requests.status`), and the download.
4. Start a DigiLocker request; capture the real response of `.../response?detail_response=true` and implement the field mapping.
5. Only then switch to production credentials/URLs and add `52.66.66.81` to `DIGIO_WEBHOOK_IPS`.

Note: the IP allowlist only works behind a trusted proxy (`TRUST_PROXY=true`, as on Render) and uses the first
`X-Forwarded-For` hop, which a caller can forge; the HMAC checksum is the real authentication, the IP list is defence in depth.

## Payments

None. The service is free (`docs/BUSINESS_MODEL.md`). An earlier Razorpay test-mode adapter was removed on 2026-11-10 and a test prevents billing code from returning.

---

## Provider Readiness Inventory (Audit — 2026-11-12)

Below is the complete readiness inventory of every external provider and infrastructure integration implemented in the repository. Staff and admins can inspect live configuration and connectivity status at runtime via `GET /admin/readiness` (never exposes secrets or calls third-party APIs).

| Provider / Integration | Purpose | Implementation Status | Required Env Vars | Sandbox / Test Support | Production Onboarding Requirements | Webhook Requirements | Retry & Failure Behavior | Current Automated Tests | Remaining Limitations |
|---|---|---|---|---|---|---|---|---|---|
| **1. Anthropic Claude (`backend/app/agent/llm.py`)** | Optional LLM fallback for ambiguous goal intake (`parse_goal`) and verbatim-quote grounded claim extraction (`extract_from_page`). Never used for form submission. | **Implemented** (`anthropic.AsyncAnthropic`). When unconfigured, `LLM.available` is `False` and the app deterministically uses the rules engine and curated seed KB. Accidental Aadhaar/PAN strings in prompts are scrubbed via `redact_str()`. | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` (both required together when enabled; checked in `production_problems()`). | Mock client injection in unit tests; deterministic fallback in local dev when env vars are empty. | Create Anthropic console account, provision API key, set `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL` on `rtn-api` and `rtn-worker`. | None | `timeout=30s` per call, `max_retries=0` on SDK client, bounded `retries=2` (max 3 attempts) with exponential backoff + `CircuitBreaker(failure_threshold=4, reset_seconds=45)`. Logs only `error_type`, never prompts or keys. | `tests/test_research.py`, `tests/test_provider_readiness.py` | Only Anthropic is implemented (`LLM.provider = "anthropic"`). Live API key not exercised in CI. |
| **2. SMTP Email (`backend/app/integrations/real/smtp.py`)** | Outgoing transactional email for password-reset links, email verification links, and citizen-consented licence reminders. | **Implemented** (`SmtpEmail` using `smtplib.SMTP` / `SMTP_SSL` in background thread). Uses `MockMessenger("email")` (`delivery_status="queued_mock"`) when `SMTP_HOST` or `SMTP_FROM` is unset. | `SMTP_HOST`, `SMTP_PORT` (`587` or `465`), `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_STARTTLS` (`true`/`false`). Required in `APP_ENV=prod`. | `MockMessenger.OUTBOX` in dev/tests; mocked `smtplib.SMTP` / `SMTP_SSL` in unit tests. | Provision transactional SMTP provider (AWS SES, Brevo, SendGrid, or NIC mail), verify sender domain SPF/DKIM/DMARC records, set `SMTP_*` env vars on `rtn-api` and `rtn-worker`. | None | `timeout=20s`, bounded `retries=1` (max 2 attempts) for transient network/`4xx` SMTP errors only; permanent `5xx` and auth errors fail immediately. Returns `smtp_accepted=True`, `recipient_delivery_confirmed=False`. Never logs recipient, body, or password. | `tests/test_password_and_email.py`, `tests/test_provider_readiness.py` | SMTP acceptance (`250 OK`) confirms handoff to the mail relay, not final inbox placement (which requires provider bounce webhooks outside scope). |
| **3. MSG91 SMS (`backend/app/integrations/real/msg91.py`)** | Outgoing SMS reminders via MSG91 v5 Flow API (`POST https://control.msg91.com/api/v5/flow`). (2FA uses RFC 6238 TOTP authenticator apps, not SMS OTP.) | **Implemented** (`Msg91Sms`). Falls back to `MockMessenger("sms")` when `MSG91_AUTHKEY` or `MSG91_TEMPLATE_ID` is empty. | `MSG91_AUTHKEY`, `MSG91_TEMPLATE_ID`, `MSG91_TEXT_VAR` (default `var1`). Both `MSG91_AUTHKEY` and `MSG91_TEMPLATE_ID` must be set together if enabled. | `MockMessenger("sms")` when unconfigured; `httpx.MockTransport` tests for Flow API payload, retries, timeouts, and DLT error codes. | 1. Register Principal Entity on an Indian telecom TRAI DLT portal. 2. Register a 6-char Sender ID (Header) and 1-variable SMS template. 3. Complete MSG91 KYC, create a Flow linked to the DLT template ID, and set `MSG91_AUTHKEY`, `MSG91_TEMPLATE_ID`, and `MSG91_TEXT_VAR`. | None | `timeout=15s`, bounded 1 retry (max 2 attempts) for network timeouts, `429`, and `5xx` only. Does not retry `4xx` or DLT rejections (`203`/`211`). Never logs `authkey`, mobile number, or message text. | `tests/test_prod_and_fetcher.py`, `tests/test_provider_readiness.py` | Request shape verified against MSG91 docs and mocked transport; not yet tested against a live MSG91 account with a DLT-approved template. |
| **4. Digio Aadhaar e-Sign (`backend/app/integrations/real/digio.py` — `DigioESign`)** | Citizen-initiated Aadhaar e-Sign of reviewed application PDFs (`POST /v2/client/document/upload`, status check, signed PDF download). | **Implemented** (`DigioClient`, `DigioESign`). Uses `MockESign` in demo mode when unconfigured; returns HTTP `503` if unconfigured when `DEMO_MODE=false`. | `DIGIO_CLIENT_ID`, `DIGIO_CLIENT_SECRET`, `DIGIO_ENV` (`sandbox`\|`production`), `DIGIO_WEBHOOK_SECRET`, `DIGIO_WEBHOOK_IPS` (optional IP allowlist when `TRUST_PROXY=true`). | `DIGIO_ENV=sandbox` (`https://ext.digio.in:444`); `MockESign` for local demo; `httpx.MockTransport` suite in `tests/test_digio.py`. | Complete Digio enterprise onboarding, obtain sandbox then production `DIGIO_CLIENT_ID` / `DIGIO_CLIENT_SECRET`, configure webhook URL & secret in Digio dashboard, run sandbox checklist above. | `POST /webhooks/digio` (`X-Digio-Checksum` HMAC-SHA256 hex of raw body; deduplicated via `webhook_events.id`; events `doc.signed`, `doc.sign.failed`, `doc.sign.rejected`). | Upload `timeout=60s` with **no retry** (`retry=False`) to prevent duplicate signing requests (also passes `callback=reference_id` for Digio idempotency). Read-only status (`30s`) and download (`60s`) retry once (`retry=True`) on network/`5xx`. | `tests/test_digio.py`, `tests/test_provider_readiness.py` | Untested against live Digio sandbox until owner receives Digio credentials. |
| **5. Digio DigiLocker (`backend/app/integrations/real/digio.py` — `DigioDigiLocker`)** | Citizen-consented document fetch via Digio DigiStudio KYC (`POST /client/kyc/v2/request/with_template`, `POST /client/kyc/v2/{id}/response`). | **Partially Implemented** (request initiation, webhook state transition, and status polling are complete; response field extraction returns `fields: {}` until verified against a real sandbox payload). | `DIGIO_CLIENT_ID`, `DIGIO_CLIENT_SECRET`, `DIGIO_ENV`, `DIGIO_WEBHOOK_SECRET`, `DIGIO_DIGILOCKER_TEMPLATE` (default `DIGILOCKER_AADHAAR_PAN`). | `DIGIO_ENV=sandbox`; `MockDigiLocker` in local demo; mocked HTTP tests in `tests/test_digio.py`. | Have Digio provision template `DIGILOCKER_AADHAAR_PAN` on sandbox/production account, capture a real sandbox response from `/client/kyc/v2/{id}/response`, and map returned fields to interview keys. | `POST /webhooks/digio` (same HMAC-SHA256 verification and `WebhookEvent` deduplication; events `DOCUMENTS_PULLED_SUCCESSFULLY`, `DOCUMENTS_PULLED_PARTIALLY`, `KYC_REQUEST_*`). | Start request `timeout=30s` (`retry=False`); status poll `timeout=30s` (`retry=True`, max 2 attempts on network/`5xx`). Rejects malformed responses lacking a valid `status` string. | `tests/test_digio.py`, `tests/test_provider_readiness.py` | **Field mapping (`fields: {}`) is intentionally unimplemented** so field names are never guessed without a real Digio sandbox payload. |
| **6. S3-Compatible Object Storage (`backend/app/core/storage.py` — `S3StorageBackend`)** | Durable object storage for user-uploaded supporting documents in the Document Vault. | **Implemented** (`LocalStorageBackend` for `STORAGE_BACKEND=local`, `S3StorageBackend` with AWS SigV4 `AWS4-HMAC-SHA256` signing for `STORAGE_BACKEND=s3`). | `STORAGE_BACKEND` (`local`\|`s3`), `STORAGE_LOCAL_DIR`, `STORAGE_BUCKET`, `STORAGE_REGION`, `STORAGE_ENDPOINT_URL`, `STORAGE_ACCESS_KEY_ID`, `STORAGE_SECRET_ACCESS_KEY`, `MAX_UPLOAD_BYTES`. | `LocalStorageBackend` used in dev/CI; `S3StorageBackend` tested via `httpx.MockTransport` in `tests/test_document_vault.py`. | Provision bucket on AWS S3, Cloudflare R2, or MinIO; set `STORAGE_BACKEND=s3` and credentials on **both** `rtn-api` and `rtn-worker`. | None | `timeout=30s` per S3 request; failed uploads clean up `.part-*` temp files or delete orphaned objects if DB commit fails. | `tests/test_document_vault.py` | When `STORAGE_BACKEND=local`, files reside on container disk (ephemeral on Render unless switched to `s3`). |
| **7. External Malware Scanner (`backend/app/core/scanner.py`)** | Pre-storage antivirus scan hook for Document Vault uploads. | **Implemented** (`DisabledMalwareScanner` when `DOCUMENT_SCAN_MODE=disabled`, `ExternalHttpMalwareScanner` when `DOCUMENT_SCAN_MODE=external`). | `DOCUMENT_SCAN_MODE` (`disabled`\|`external`), `DOCUMENT_SCAN_URL`. | `disabled` mode in dev/CI; mocked HTTP scanner tests (clean, infected `422`, unreachable `503`) in `tests/test_document_vault.py`. | Deploy an HTTP antivirus scanning service (e.g., ClamAV REST wrapper) and set `DOCUMENT_SCAN_MODE=external` and `DOCUMENT_SCAN_URL`. | None | `timeout=20s`; fails closed (`503 scanner_unavailable`) when `DOCUMENT_SCAN_MODE=external` and the scanner is unreachable or returns invalid JSON. | `tests/test_document_vault.py` | Disabled by default (`scan_status="disabled"`), explicitly disclosed in UI and docs. |
| **8. Redis (`backend/app/core/middleware.py`, `cache.py`, `jobs/worker.py`)** | Distributed `/auth` and API rate limiting (`MULTI`/`EXEC` `INCR`+`EXPIRE`), non-sensitive caching, and `arq` background job queue. | **Implemented**. Rate limiter and cache fail open to bounded in-memory fallbacks (`max_keys=10,000`) when `REDIS_URL` is unset or unreachable. | `REDIS_URL` | In-memory fallback when `REDIS_URL=""`; fake/unreachable Redis tests in `tests/test_ops.py`. | Provision Redis 7 (`rtn-redis` in `render.yaml` / `docker-compose.prod.yml`) and set `REDIS_URL` on `rtn-api` and `rtn-worker`. | None | `1.0s` socket connect/read timeout on rate limiter and cache; logs PII-free warning and degrades to in-memory on outage. | `tests/test_ops.py` | Background `arq` worker requires live Redis to execute scheduled cron jobs. |
| **9. Sentry (`backend/app/core/errors.py`) & OpenTelemetry (`backend/app/core/tracing.py`)** | Unhandled exception reporting (`send_default_pii=False`) and distributed OTLP span export. | **Implemented** (optional hooks; no-op when env vars are unset or optional SDK packages are absent). | `SENTRY_DSN`, `OTEL_EXPORTER_OTLP_ENDPOINT` | Tested with no-op / span unit tests in `tests/test_ops.py`. | Optional: create Sentry project / OTLP collector and set `SENTRY_DSN` / `OTEL_EXPORTER_OTLP_ENDPOINT`. | None | Never blocks request handling; `send_default_pii=False` prevents PII transmission. | `tests/test_ops.py` | Optional observability integrations. |
| **10. WhatsApp Business & UMANG (`backend/app/integrations/real/messaging.py`, `umang.py`)** | WhatsApp reminder channel and UMANG service directory lookup. | **Unimplemented Stubs** (`RealMessenger`, `RealUMANG` raise `NotImplementedError`; `MockMessenger("whatsapp")` and `MockUMANG` used in mock mode). | None yet | `MockMessenger("whatsapp")`, `MockUMANG` | Requires Meta/BSP WhatsApp Business API onboarding and MeitY/NeGD UMANG partner agreement + adapter implementation. | None | `dispatch_due()` catches `NotImplementedError` so a failing channel never blocks email/SMS reminders. | `tests/test_password_and_email.py` | Stubs only; not active in production. |
