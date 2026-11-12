 # Red Tape Navigator — Final Project & Production Readiness Audit

**Repository:** `https://github.com/RajdipDhar2007/Red_Tape_Navigator`  
**Audit Date:** 2026-04-16  
**Audited Commit / Workspace:** `d:/Hack_N_Pitch/Red_Tape_Navigator` (`main`)  
**Roles Applied:** Senior Software Architect, Staff Full-Stack Engineer, AI Engineer, DevSecOps Engineer, QA Lead  

> **Core Invariants Verified:**
> - **100% Free Forever:** Enforced in code via `backend/tests/test_free_forever.py` — zero payment/billing SDKs, routes, or UI strings exist.
> - **Human-in-the-Loop Government Filing:** The system never auto-submits applications to government portals (`ps.md` invariant). It prepares filled PDFs, official checklists, and review queues; final submission remains strictly under citizen control.
> - **Zero Hallucinated Legal Facts:** All fees, SLA days, citations, penalties, and portal URLs originate from the deterministic YAML knowledge base (`backend/app/kb/seeds/*.yaml`, 438 rules across 20 cities and 15 states/UTs) or citation-verified RAG claims (`backend/app/agent/research.py`).

---

## 1. Existing Architecture

### 1.1 Monorepo Structure
| Directory / File | Purpose |
|---|---|
| `backend/` | Python 3.11+ FastAPI asynchronous API server, SQLAlchemy 2.0 ORM, Alembic migrations, deterministic intake/planner/interview/PDF engine, and `arq` background worker |
| `frontend/` | Next.js 14.2 (App Router, TypeScript 5.5, `next-intl` i18n for `en`/`hi`/`bn`, standalone Docker output) |
| `scripts/` | Operational maintenance scripts (`rule_freshness.py` CI gate, `rotate_encryption_key.py` Fernet key rotation) |
| `deploy/` & `infra/` | Reverse proxy config (`deploy/Caddyfile`) and AWS App Runner + RDS + ECR IaC (`infra/terraform/main.tf`) |
| `render.yaml` | Render Blueprint for managed PostgreSQL, Redis, API service (`rtn-api`), and worker (`rtn-worker`) |
| `docker-compose.yml` / `docker-compose.prod.yml` | Local development and production container orchestration (`db`, `redis`, `api`, `worker`, `web`, `caddy`) |
| `.github/workflows/` | `ci.yml` (Backend pytest/ruff/mypy + Postgres migration round-trip + AI evals + rule freshness + Frontend lint/typecheck/vitest/build + Docker compose smoke test) and `deploy.yml` (GHCR multi-service container publish) |

### 1.2 Request & Processing Pipeline
```mermaid
flowchart LR
    Citizen["Citizen / Browser (en, hi, bn)"] --> NextJS["Next.js 14 App Router"]
    NextJS -->|REST + Bearer JWT| FastAPI["FastAPI Backend (/api/v1)"]
    FastAPI --> MW["Middleware Stack (CORS, SecHeaders, RateLimit, RequestContext)"]
    MW --> Auth["Auth / RBAC / 2FA / Workspace Check"]
    Auth --> Intake["Deterministic Intake + Optional Grounded LLM"]
    Intake --> KB["YAML Rule Store (20 Cities, 438 Rules) + pgvector RAG"]
    KB --> Interview["Adaptive Interview Engine + Field Memory + DigiLocker"]
    Interview --> PDF["ReportLab / pypdf Filler + Staff Review Queue + Digio eSign"]
    PDF --> Followup["Reminders (SMTP / MSG91) + Renewal Engine (arq + Redis)"]
```

### 1.3 Key Architectural Patterns
- **Deterministic-First AI Architecture (`backend/app/agent/`):**
  - `intake.py` resolves city (with alias normalization, e.g., `bangalore -> bengaluru`, `gurgaon -> gurugram`) and business type using keyword matching first, falling back to structured LLM extraction (`llm.py`) only when ambiguous.
  - `planner.py` constructs the ordered dependency graph of Central, State, and Municipal licences solely from verified YAML rules (`app/kb/store.py`) and adjusts ordering for clinic/pharma/import-export prerequisites.
  - `research.py` enforces strict citation grounding: every claim returned by the LLM must reference an existing `Claim.id` in the database; unknown IDs or raw numbers not present in source claims are stripped.
- **Field-Level PII Encryption (`backend/app/core/crypto.py`):**
  - Sensitive answers (`aadhaar`, `pan`, `bank_account_number`) and TOTP secrets (`User.totp_secret`) are encrypted at rest with `MultiFernet` (`FIELD_ENCRYPTION_KEY`, with rotation support via `FIELD_ENCRYPTION_KEY_PREVIOUS`).
  - Regex-based PII redaction scrubs 12-digit Aadhaar and 10-character PAN patterns from structured logs and audit payloads.
- **Tamper-Evident Audit Chain (`backend/app/core/audit.py`):**
  - Every state-changing event appends a row to `audit_log` with `entry_hash = SHA-256(seq | prev_hash | actor | action | target | payload | timestamp)`, verifiable via `GET /api/v1/admin/audit/verify`.

---

## 2. Completed Features

### 2.1 Backend Features (Implemented & Verified by Automated Tests)
1. **Authentication & Account Security (`app/api/auth.py`, `app/core/security.py`, `app/core/totp.py`):**
   - Registration (`POST /auth/register`), login (`POST /auth/login`), token rotation (`POST /auth/refresh`, `POST /auth/logout`) with reuse detection (presenting a revoked refresh token revokes all tokens for that user).
   - Account lockout after 5 failed login attempts for 15 minutes (`MAX_FAILED_LOGINS = 5`).
   - Password reset flow (`POST /auth/password/forgot`, `POST /auth/password/reset`) with SHA-256 hashed one-time tokens.
   - Email verification flow (`POST /auth/verify-email/send`, `POST /auth/verify-email/confirm`).
   - RFC 6238 TOTP Two-Factor Authentication (`POST /auth/2fa/setup`, `POST /auth/2fa/enable`, `POST /auth/2fa/disable`) with 8 PBKDF2-HMAC-SHA256 single-use recovery codes.
2. **Multi-Tenant Team Workspaces (`app/api/workspaces.py`):**
   - Create workspace, list workspaces, invite members by email (`owner`/`admin`/`editor`/`viewer` roles), accept invitation by token, remove member, and scope sessions via `X-Workspace-Id` header.
3. **Knowledge Base & Regulatory Coverage (`app/kb/`):**
   - **20 Indian cities across 15 states/UTs** (`bengaluru`, `mumbai`, `delhi`, `hyderabad`, `chennai`, `kolkata`, `pune`, `ahmedabad`, `jaipur`, `lucknow`, `indore`, `chandigarh`, `kochi`, `coimbatore`, `surat`, `nagpur`, `visakhapatnam`, `bhopal`, `guwahati`, `patna`).
   - **9 business types** (`restaurant`, `cloud_kitchen`, `kirana`, `clinic`, `pharmacy`, `salon`, `saas`, `manufacturing`, `export_import`).
   - **438 verified rules** with official portal URLs, statutory citations, fee breakdowns, SLA days, penalties, and document checklists.
   - Confidence decay scoring (`app/kb/confidence.py`: `high` ≤ 60 days, `medium` ≤ 90 days, `low` > 90 days) and localized field rendering (`en`, `hi`, `bn` via `app/core/localize.py`).
4. **Session Workflow & Adaptive Interview (`app/api/sessions.py`, `app/services/session_service.py`, `app/interview/`):**
   - `POST /sessions` intake, `POST /sessions/{id}/clarify` multi-turn disambiguation, `POST /sessions/{id}/select-licences`.
   - Deduplicated union of required fields across selected licences (`fields.py`), pre-filled from cross-session `UserMemory` (`memory.py`).
   - Strict Indian format validators (`validators.py`): Verhoeff checksum for 12-digit Aadhaar, PAN regex (`^[A-Z]{5}[0-9]{4}[A-Z]$`), GSTIN 15-char checksum, IFSC (`^[A-Z]{4}0[A-Z0-9]{6}$`), 6-digit PIN, 10-digit Indian mobile (`6-9`), email, date, and positive integer checks.
   - Voice speech-to-text normalization (`POST /sessions/{id}/voice-normalize`) for Hindi/Bengali/English spoken digits and symbols (`"at the rate"`, `"dot"`, Devanagari/Bengali numerals).
5. **PDF Generation, Official AcroForm Overlay & Human Review (`app/forms/`):**
   - `filler.py` generates bilingual-safe multi-page PDF packs with ReportLab (including CJK/Indic font fallback) and stamps watermarks (`PREPARED BY RED TAPE NAVIGATOR - REVIEW BEFORE SUBMITTING` and `DRAFT - PENDING HUMAN REVIEW`).
   - `official.py` supports fetching official government PDFs (HTTPS-only, `%PDF-` header check, 8 MB cap, SHA-256 hash verification), AcroForm field filling (`pypdf`), or coordinate overlay (`registry.py`).
   - High-risk licences (`fssai_state`, `drug_licence`, `fire_noc`, `pcb_consent`, `clinical_establishment`, `factory_licence`, `iec_code`) automatically create a `ReviewItem` requiring staff approval before download is unlocked.
6. **Admin & Staff Operations (`app/api/admin.py`):**
   - `GET /admin/stats`, `GET /admin/rule-freshness`, `GET /admin/reviews`, `POST /admin/reviews/{id}` (approve/reject), `POST /admin/users/{id}/role`, `POST /admin/forms/{licence_id}/fetch`, `POST /admin/forms/{id}/activate`, `GET /admin/forms/{licence_id}`, `POST /admin/purge`, `GET /admin/audit/verify`.
7. **Privacy & DPDP Compliance Endpoints (`app/api/privacy.py`, `app/api/consent.py`):**
   - `POST /consent` and `GET /consent` (`consent_records` table).
   - `GET /privacy/export` (full JSON export of user profile, sessions, decrypted answers, memories, reminders, consents).
   - `DELETE /privacy/sessions/{sid}` and `DELETE /privacy/me` (account erasure + audit anonymization), plus automated 180-day retention purge (`purge_expired`).

### 2.2 Frontend Features (Implemented & Verified by Build/Tests)
1. **Localized Citizen Journey (`frontend/app/[locale]/`, `messages/{en,hi,bn}.json`):**
   - Complete 3-language support (`en`, `hi`, `bn`) with parity-tested message keys (`frontend/tests/messages.test.ts`).
   - [`Home.tsx`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/frontend/components/Home.tsx): Goal intake input, Web Speech API [`VoiceInput.tsx`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/frontend/components/VoiceInput.tsx), 4 example scenario cards, recent sessions list, DPDP consent modal, and link to `/[locale]/facts`.
   - [`SessionView.tsx`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/frontend/components/SessionView.tsx): 5-step progress indicator (`Goal -> Checklist -> Interview -> Review -> Pack`), clarify prompt, [`ChecklistView.tsx`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/frontend/components/ChecklistView.tsx), [`InterviewChat.tsx`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/frontend/components/InterviewChat.tsx) (DigiLocker connect + manual input + voice input), [`ReviewView.tsx`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/frontend/components/ReviewView.tsx) (inline answer editing + human review status banner), and [`DoneView.tsx`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/frontend/components/DoneView.tsx) (PDF download, e-Sign trigger, renewal scheduler, step-by-step official portal submission guide).
2. **Account, Teams, Staff & Legal Pages:**
   - [`KeyInSheet.tsx`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/frontend/components/KeyInSheet.tsx) (Sign-in, Register, 2FA code prompt, Forgot Password).
   - [`AccountView.tsx`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/frontend/components/AccountView.tsx) (Email verification, TOTP 2FA setup/disable + recovery codes display, password change).
   - [`TeamsView.tsx`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/frontend/components/TeamsView.tsx) (Workspace switcher, create team, member invite, copy invite link).
   - [`StaffConsole.tsx`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/frontend/components/StaffConsole.tsx) (Metrics cards, official PDF template fetch/activate, pending review queue approve/reject).
   - [`PolicyFacts.tsx`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/frontend/components/PolicyFacts.tsx) (`/[locale]/facts` filterable table of all 20 cities and 438 rules with source links and confidence badges).
   - [`LegalPage.tsx`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/frontend/components/LegalPage.tsx) (`/[locale]/privacy`, `/[locale]/terms`, `/[locale]/disclaimer`).

---

## 3. Incomplete Features

1. **Digio DigiLocker Document Field Extraction (`backend/app/integrations/real/digio.py:165-184`):**
   - `DigioDigiLocker.start_Link()` and `get_status()` are implemented, and webhook verification (`app/api/webhooks.py`) transitions `ExternalRequest` state to `approved`.
   - However, `DigioDigiLocker.get_status()` currently returns `{"status": status, "fields": {}}` with an explicit comment: *"Field extraction from the Digio response payload is deliberately NOT done here — the payload shape depends on which doc types the template requested."* Until mapped against a live Digio sandbox response, production DigiLocker flows mark the session as approved without populating `Answer` records.
2. **Citizen Self-Service DPDP Controls in Frontend (`frontend/components/AccountView.tsx`):**
   - Backend provides `GET /api/v1/privacy/export`, `DELETE /api/v1/privacy/me`, `DELETE /api/v1/privacy/sessions/{sid}`, and `POST /api/v1/consent` (`granted: false`).
   - However, [`AccountView.tsx`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/frontend/components/AccountView.tsx) and [`Home.tsx`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/frontend/components/Home.tsx) have no UI buttons for citizens to download their personal data JSON, delete individual sessions, withdraw consent, or delete their account, despite `docs/COMPLIANCE.md` stating these are available from the Account sheet.
3. **Admin Console UI Coverage (`frontend/components/StaffConsole.tsx`):**
   - Backend exposes `GET /api/v1/admin/rule-freshness`, `GET /api/v1/admin/audit/verify`, `POST /api/v1/admin/users/{uid}/role`, and `POST /api/v1/admin/purge`.
   - [`StaffConsole.tsx`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/frontend/components/StaffConsole.tsx) only renders `GET /admin/stats`, `POST /admin/forms/{licence}/fetch`, and `GET/POST /admin/reviews`. It has no UI tabs for rule freshness monitoring, audit-chain verification, user role management, or retention purge.
4. **Sentry Error Tracking Dependency (`backend/app/core/errors.py`, `backend/pyproject.toml`):**
   - `app/core/errors.py` initializes `sentry_sdk` when `SENTRY_DSN` is set, and deployment configs pass `SENTRY_DSN`. However, `sentry-sdk` is not listed in `backend/pyproject.toml`, so `import sentry_sdk` always catches ` Exception` and logs `sentry_dsn_set_but_sdk_missing`.
5. **WhatsApp & UMANG Real Adapters (`backend/app/integrations/real/messaging.py`, `umang.py`):**
   - Both modules exist only as stubs that raise `NotImplementedError("Wire up Gupshup/Twilio...")` and `NotImplementedError("Register as UMANG Partner...")`.

---

## 4. Missing Features

Comparing the codebase against the project handoff notes and the audit requirements:

1. **Gemini API Provider in LLM Adapter (`backend/app/agent/llm.py`):**
   - (Resolved: `app/agent/llm.py` now supports Ollama, Gemini (REST via `httpx`, `GEMINI_API_KEY` + `GEMINI_MODEL`) and Anthropic, chosen by `LLM_PROVIDER`; see `backend/tests/test_llm_providers.py`.)
2. **Citizen Document Upload & Vault (Backend + Frontend):**
   - The system generates filled application PDFs from interview text answers, but citizens cannot upload supporting attachment files (e.g., electricity bill, rent agreement, NOC, passport photo, shop photo) or store them in an encrypted document vault for reuse across licence applications.
3. **Object Storage Adapter (S3 / Cloudflare R2 / GCS):**
   - No object storage integration exists. Official PDF templates fetched by admins are stored as `LargeBinary` blobs directly in PostgreSQL (`form_sources.pdf`), and signed PDFs are streamed transiently from Digio without persistent storage.
4. **Partner Portal (CA / CSC / Facilitator Multi-Client Dashboard):**
   - While team workspaces (`/teams`) allow sharing sessions via `X-Workspace-Id`, there is no dedicated Partner Portal (`/partner`) for Chartered Accountants or Common Service Centres (CSCs) to manage multiple client businesses, track bulk licence expiries, or filter client compliance status.
5. **Help Centre / FAQ & Citizen Support Ticket Flow:**
   - No `/[locale]/help` route, searchable FAQ, or support request/feedback submission flow exists.
6. **Renewal `.ics` Calendar Export:**
   - [`DoneView.tsx`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/frontend/components/DoneView.tsx) allows scheduling server-side reminders (`/sessions/{id}/schedule-renewals`), but lacks an "Add to Calendar (`.ics`)" download button for Google/Outlook/Apple Calendar.
7. **SEO & Discoverability (`sitemap.xml`, `robots.txt`, OpenGraph, Public Licence Guides):**
   - `frontend/app/` has no `sitemap.ts`, `robots.ts`, OpenGraph/Twitter metadata tags, or indexable `/[locale]/licences/[city]/[licence]` static landing pages.
8. **Progressive Web App (PWA) Support:**
   - `frontend/public/` directory does not exist; there is no `manifest.webmanifest`, app icons, or offline service worker for low-connectivity citizens.

---

## 5. Critical Bugs

### 5.1 `[P0]` Encryption Key Rotation Locks Out All 2FA Users & Crashes Recovery Code Login
- **Locations:** [`scripts/rotate_encryption_key.py`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/scripts/rotate_encryption_key.py#L22-L44) and [`backend/app/api/auth.py`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/backend/app/api/auth.py#L189-L202)
- **Root Cause:**
  1. `User.totp_secret` (added in migration `0007_totp_2fa.py`) is encrypted using `app.core.crypto.encrypt(secret)` (`app/api/auth.py:298`).
  2. However, `scripts/rotate_encryption_key.py` only selects and re-encrypts `Answer` rows (`select(Answer).where(Answer.sensitive.is_(True))`) and **never rotates `User.totp_secret`**.
  3. Furthermore, in `_consume_second_factor(user, code)` (`app/api/auth.py:189-192`), `totp.verify(decrypt(user.totp_secret), code)` executes **before** checking `user.recovery_hashes` and does not catch `cryptography.fernet.InvalidToken`.
- **Impact:** After an operator follows the documented key-rotation procedure (`docs/SECURITY.md` §1) and removes `FIELD_ENCRYPTION_KEY_PREVIOUS`, every 2FA-enabled user's `totp_secret` fails to decrypt, raising an unhandled `InvalidToken` (HTTP 500) on login—even if the user enters a valid backup recovery code.

### 5.2 `[P0]` PostgreSQL Foreign-Key Violation Breaks DPDP Account Erasure, Session Deletion & Retention Purge
- **Locations:** [`backend/app/services/privacy.py`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/backend/app/services/privacy.py#L63-L70) and [`backend/migrations/versions/0004_external_requests.py`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/backend/migrations/versions/0004_external_requests.py#L16-L31)
- **Root Cause:**
  - `ExternalRequest.session_id` has a non-nullable `ForeignKey("nav_sessions.id")` without `ON DELETE CASCADE` (`app/db/models.py:188`).
  - `app/services/privacy.py:_delete_session_data()` deletes `Answer`, `Reminder`, `ReviewItem`, and `NavSession`, but **omits `delete(ExternalRequest).where(ExternalRequest.session_id.in_(session_ids))`**.
  - Because unit tests run on SQLite without `PRAGMA foreign_keys=ON`, this bug was masked in `tests/test_privacy_and_admin.py`.
- **Impact:** On production PostgreSQL, whenever a session has used DigiLocker or e-Sign (`external_requests` row exists), calling `DELETE /api/v1/privacy/sessions/{sid}`, `DELETE /api/v1/privacy/me` (DPDP Right to Erasure), or running `purge_expired` (`POST /api/v1/admin/purge` / nightly `arq` cron) crashes with `sqlalchemy.exc.IntegrityError: update or delete on table "nav_sessions" violates foreign key constraint "external_requests_session_id_fkey"`.

### 5.3 `[P1]` Production Docker Compose Drops All `MSG91_*` and `DIGIO_*` Environment Variables
- **Location:** [`docker-compose.prod.yml`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/docker-compose.prod.yml#L33-L54)
- **Root Cause:** `.env.prod.example` documents `MSG91_AUTHKEY`, `MSG91_SENDER_ID`, `MSG91_TEMPLATE_ID`, `MSG91_TEXT_VAR`, `DIGIO_CLIENT_ID`, `DIGIO_CLIENT_SECRET`, `DIGIO_ENV`, `DIGIO_WEBHOOK_SECRET`, `DIGIO_WEBHOOK_IPS`, and `DIGIO_DIGILOCKER_TEMPLATE`. However, the `&api-env` anchor in `docker-compose.prod.yml` does not pass any of these variables into the `api` or `worker` containers, nor does it specify `env_file: .env.prod`.
- **Impact:** Setting `INTEGRATIONS_MODE=real` in a `docker-compose.prod.yml` deployment causes the API and worker to fail startup validation (`app/core/config.py:validate_for_Startup()`) because `DIGIO_*` and `MSG91_*` evaluate to empty strings inside the container.

### 5.4 `[P1]` Render Worker Missing `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, and `SENTRY_DSN`
- **Location:** [`render.yaml`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/render.yaml#L68-L100)
- **Root Cause:** `rtn-worker` runs `refresh_rules` (weekly scraper + LLM diff summarizer) and background jobs, but `render.yaml` only defines `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, and `SENTRY_DSN` on `rtn-api`, omitting them on `rtn-worker`.

### 5.5 `[P1]` `bank_account_number` Omitted from `app/core/crypto.py:SENSITIVE_KEYS`
- **Locations:** [`backend/app/core/crypto.py`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/backend/app/core/crypto.py#L10) vs. [`backend/app/interview/fields.py`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/backend/app/interview/fields.py#L50-L58)
- **Root Cause:** `fields.py` defines `SENSITIVE_KEYS = {"aadhaar", "pan", "bank_account_number"}` for database encryption, whereas `crypto.py` defines `SENSITIVE_KEYS = {"aadhaar", "pan", "aadhaar_number", "pan_number"}` (missing `"bank_account_number"`).
- **Impact:** Any dictionary passed through `crypto.redact()` (such as structured logs or audit log payloads) will not automatically mask a key named `bank_account_number`.

### 5.6 `[P1]` Concurrent Audit Log Writes Can Fork the SHA-256 Hash Chain
- **Location:** [`backend/app/core/audit.py`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/backend/app/core/audit.py#L31-L58)
- **Root Cause:** `audit.record()` queries `select(AuditLog).order_by(AuditLog.seq.desc()).limit(1)` without row-level locking (`with_for_update()`) or serialization. Under concurrent requests, two transactions read the same `prev_hash`, producing two entries that reference the same predecessor and causing `GET /api/v1/admin/audit/verify` to report `chain_valid: false`.

### 5.7 `[P1]` Clarify Input Not Cleared & Errors Unhandled in `SessionView.tsx`
- **Location:** [`frontend/components/SessionView.tsx`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/frontend/components/SessionView.tsx#L76-L92)
- **Root Cause:** Submitting the clarification form calls `void post('/sessions/${id}/clarify', { answer }).then(load)` without clearing `answer` (`setAnswer("")`), without disabling the button during submission, and without a `.catch()` block. When both city and business type need clarification in sequence, the user's first answer stays pre-filled in the text box for the second question, and network/API failures result in unhandled promise rejections.

---

## 6. Security Vulnerabilities and Risks

| Severity | Finding | Location | Risk & Remediation |
|---|---|---|---|
| **High (P0)** | **DPDP Erasure Failure on `ExternalRequest` FK** | [`app/services/privacy.py:63`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/backend/app/services/privacy.py#L63) | Prevents citizens who used DigiLocker/eSign from deleting their account or sessions on PostgreSQL (DPDP Act §12 violation). Delete `ExternalRequest` rows before deleting `NavSession`. |
| **High (P0)** | **2FA Lockout on Encryption Key Rotation** | [`scripts/rotate_encryption_key.py:25`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/scripts/rotate_encryption_key.py#L25), [`app/api/auth.py:191`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/backend/app/api/auth.py#L191) | Rotating `FIELD_ENCRYPTION_KEY` orphans `User.totp_secret` and blocks recovery codes. Rotate `User.totp_secret` in the script and wrap `decrypt()` in `try/except InvalidToken` before checking recovery hashes. |
| **Medium (P1)** | **PII Redaction Misses `bank_account_number`** | [`app/core/crypto.py:10`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/backend/app/core/crypto.py#L10) | Add `"bank_account_number"` and `"ifsc"` to `crypto.SENSITIVE_KEYS`. |
| **Medium (P1)** | **In-Memory Rate Limiter Not Shared Across Workers & Unbounded IP Dict** | [`app/core/middleware.py:50-80`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/backend/app/core/middleware.py#L50-L80) | `RateLimiter` uses per-process `defaultdict(deque)`. With `--workers 2` (or multiple replicas), effective limits double, and `self.hits` never deletes empty IP keys. Back rate limiting with Redis (falling back to bounded LRU in-memory deque). |
| **Medium (P1)** | **No Brute-Force Lockout on `/auth/2fa/enable` & `/auth/2fa/disable`** | [`app/api/auth.py:303-336`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/backend/app/api/auth.py#L303-L336) | Unlike `/auth/login`, wrong codes sent to `/auth/2fa/enable` or `/auth/2fa/disable` do not increment `user.failed_logins`. Increment `failed_logins` and enforce lockout on repeated failures. |
| **Medium (P2)** | **JWT Access & Refresh Tokens Stored in `sessionStorage`** | [`frontend/lib/api.ts:24-44`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/frontend/lib/api.ts#L24-L44) | `sessionStorage` is readable by any script executing in the origin (XSS). While CSP (`script-src 'self' 'unsafe-inline'`) mitigates external script injection, migrating refresh tokens to `HttpOnly; Secure; SameSite=Lax` cookies is recommended for defense-in-depth. |
| **Low (P2)** | **6 Moderate Dev-Time npm Advisories (`next` 14.2.15, `esbuild`/vitest)** | `frontend/package-lock.json` | `npm audit` reports 6 moderate vulnerabilities in dev tooling (`esbuild` dev server in `vitest`) and Next.js image optimization / PPR (neither feature is enabled in `next.config.mjs`). Bumping `next` to latest `14.2.x` patch and `vitest` resolves them. |

---

## 7. API Integration Requirements

Every external integration was inspected across `backend/app/integrations/`, `backend/app/core/`, `backend/app/agent/`, and `backend/tests/`:

| Integration | Audit Classification | Evidence in Codebase | Exact Requirements for Production Completion |
|---|---|---|---|
| **Gemini API** | `IMPLEMENTED` | `app/agent/llm.py` + `app/core/llm_http.py` call the Gemini REST API with JSON-schema output; settings `GEMINI_API_KEY`, `GEMINI_MODEL`, `LLM_PROVIDER`. | Set the key and model on the host; with none set the product uses its deterministic fallback. |
| **Anthropic API (optional)** | `IMPLEMENTED AND TESTED` | [`app/agent/llm.py`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/backend/app/agent/llm.py) (`AsyncAnthropic` with circuit breaker, 20s timeout, JSON extractor, and graceful no-op fallback when key is unset). Tested in `tests/test_agent_and_api.py`. | Optional. Set `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL=claude-haiku-4-5-20251001` (and add to `rtn-worker` in `render.yaml`). App works 100% deterministically without it. |
| **SMTP / Brevo** | `IMPLEMENTED AND TESTED` | [`app/integrations/real/smtp.py`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/backend/app/integrations/real/smtp.py) (`smtplib.SMTP` / `SMTP_SSL`, STARTTLS, CRLF header-injection sanitizer, `asyncio.to_thread`). Unit-tested in `tests/test_password_and_email.py`. | Provision Brevo (free tier: 300 emails/day) or AWS SES SMTP credentials; verify sender domain SPF/DKIM; set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`. |
| **MSG91** | `IMPLEMENTED AND TESTED` *(mocked HTTP; untested against live DLT)* | [`app/integrations/real/msg91.py`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/backend/app/integrations/real/msg91.py) (`POST https://control.msg91.com/api/v5/flow`, 10-digit Indian mobile validation, 3x exponential backoff on 5xx/429). Tested with `httpx.MockTransport` in `tests/test_prod_and_fetcher.py`. | Human action required: TRAI DLT principal entity registration + 6-char sender ID + approved DLT template ID. Set `MSG91_AUTHKEY`, `MSG91_SENDER_ID`, `MSG91_TEMPLATE_ID`, `MSG91_TEXT_VAR`. |
| **Digio (eSign & DigiLocker)** | `PARTIALLY IMPLEMENTED` | [`app/integrations/real/digio.py`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/backend/app/integrations/real/digio.py) & [`app/api/webhooks.py`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/backend/app/api/webhooks.py). `DigioESign` (upload PDF, get status, stream signed PDF) and HMAC-SHA256 webhook verification (`X-Digio-Checksum` + IP allowlist) are implemented and unit-tested (`tests/test_digio.py`). However, `DigioDigiLocker.get_status` returns `fields: {}` (line 183). | 1. Implement DigiLocker `fields` extraction in `DigioDigiLocker.get_status()` for Aadhaar/PAN/GSTIN payload shapes.<br>2. Sign Digio aggregator agreement & obtain sandbox/prod credentials (`DIGIO_CLIENT_ID`, `DIGIO_CLIENT_SECRET`, `DIGIO_WEBHOOK_SECRET`, `DIGIO_DIGILOCKER_TEMPLATE`). |
| **PostgreSQL (+ pgvector)** | `IMPLEMENTED AND TESTED` | [`app/db/session.py`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/backend/app/db/session.py), [`app/db/models.py`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/backend/app/db/models.py), migrations `0001`–`0007` (including `CREATE EXTENSION IF NOT EXISTS vector` and `Vector(256)` in `0001_initial.py`). Tested in CI on `pgvector/pgvector:pg16`. | Fix P0 `ExternalRequest` FK deletion bug in `app/services/privacy.py`. Provision managed PostgreSQL 16 with `pgvector` in an India region (`ap-south-1`). |
| **Redis** | `IMPLEMENTED AND TESTED` | [`app/core/cache.py`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/backend/app/core/cache.py) (`RedisCache` with automatic fallback to `MemoryCache`) and [`app/jobs/worker.py`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/backend/app/jobs/worker.py) (`arq` worker & cron jobs). Tested in `tests/test_ops_and_polish.py` and CI `compose-smoke`. | Provision managed Redis 7 (`REDIS_URL`). Recommended P1 enhancement: wire `RateLimiter` in `app/core/middleware.py` to Redis so rate limits apply globally across API workers. |
| **Object Storage** | `NOT IMPLEMENTED` | No S3/R2/GCS client or config exists. Official PDFs are stored in PostgreSQL `form_sources.pdf` (`LargeBinary`). | Optional for MVP (PostgreSQL `LargeBinary` works for the ~15 official PDF templates at < 8 MB each), or implement an S3/Cloudflare R2 adapter if citizen document uploads (vault) are added. |
| **Sentry** | `PARTIALLY IMPLEMENTED` | [`app/core/errors.py`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/backend/app/core/errors.py) defines `init_error_tracking()` and `capture_exception()`, with `pii_Removed` `before_send` hook (`send_default_pii=False`). However, `sentry-sdk` is missing from `backend/pyproject.toml`, and frontend has no Sentry setup. | Add `sentry-sdk>=2.0.0` to `backend/pyproject.toml` dependencies (or `[project.optional-dependencies]`) and add `SENTRY_DSN` to `rtn-worker` in `render.yaml`. |
| **OpenTelemetry** | `IMPLEMENTED AND TESTED` | [`app/core/tracing.py`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/backend/app/core/tracing.py) configures `TracerProvider`, `BatchSpanProcessor`, and `OTLPSpanExporter` when `OTEL_EXPORTER_OTLP_ENDPOINT` is set. `opentelemetry-api`, `opentelemetry-sdk`, and `opentelemetry-exporter-otlp-proto-http` are installed in `pyproject.toml`. | Set `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_SERVICE_NAME` in production if exporting traces to Grafana Tempo / Honeycomb / Jaeger. |

---

## 8. Database and Storage Assessment

### 8.1 Schema & Migrations Inventory (`backend/migrations/versions/`)
All 7 Alembic revisions form a clean linear chain (`0001 -> 0002 -> 0003 -> 0004 -> 0005 -> 0006 -> 0007`) and support full `upgrade head` and `downgrade base` round-trips:

| Revision | Tables Created / Altered | Assessment |
|---|---|---|
| `0001_initial.py` | `users`, `nav_sessions`, `answers`, `user_memories`, `claims` (`Vector(256)`), `reminders`, `audit_log`, `consent_records`, `review_items` | Solid schema; `pgvector` extension cleanly guarded by `if dialect == "postgresql"`. |
| `0002_refresh_tokens.py` | `refresh_tokens` (`token_hash` unique, `revoked`) | Supports rotation and token-family revocation on reuse. |
| `0003_auth_lockout_and_form_sources.py` | Adds `failed_logins`, `locked_until` to `users`; creates `form_sources` (`pdf` `LargeBinary`) | Stores official government PDFs in DB (`LargeBinary` capped at 8 MB in app layer). |
| `0004_external_requests.py` | `external_requests` (`session_id`, `user_id`, `provider`, `kind`, `external_id`, `status`) | **Bug Found:** `session_id` FK to `nav_sessions.id` lacks `ON DELETE CASCADE` and is omitted in `privacy.py:_delete_session_data`. |
| `0005_password_resets_and_email_verification.py` | Adds `email_verified` to `users`; creates `one_time_tokens` (`purpose`, `token_hash`) | Clean SHA-256 token storage with expiry and consumption tracking. |
| `0006_workspaces.py` | `workspaces`, `workspace_members`, `workspace_invites`; adds `workspace_id` FK to `nav_sessions` | Note: `nav_sessions.workspace_id` and `workspace_members.workspace_id` lack DB-level `ON DELETE CASCADE` (currently workspaces cannot be deleted via API). |
| `0007_totp_2fa.py` | Adds `totp_secret`, `totp_enabled`, `recovery_hashes` (`JSON`) to `users` | **Bug Found:** `totp_secret` is encrypted with Fernet but omitted from `scripts/rotate_encryption_key.py`. |

### 8.2 Vector Search & Embeddings (`backend/app/kb/embedding.py`)
- Uses a deterministic 256-dimensional hashed bag-of-ngrams embedding (`embed_text`) stored in `claims.embedding` (`Vector(256)` on PostgreSQL, `JSON` on SQLite).
- Zero external embedding API cost; works offline and deterministically across tests and production.

### 8.3 Storage Assessment
- **Static Form Placeholders:** Stored in git under `backend/app/forms/templates/*.pdf` (~15 lightweight placeholder PDFs).
- **Official Government PDFs:** Stored in PostgreSQL `form_sources.pdf` (`LargeBinary`, max 8 MB per version). While acceptable for 15–50 official blank templates, storing binary blobs in PostgreSQL increases `pg_dump` size over time. Old inactive versions should either be pruned or moved to object storage if template volume grows.

---

## 9. Deployment Blockers

### 9.1 Code-Level Blockers (Can Be Fixed Immediately in Repository)
1. **[P0] Fix `ExternalRequest` deletion in `app/services/privacy.py`** so DPDP erasure (`DELETE /privacy/me`), session deletion (`DELETE /privacy/sessions/{sid}`), and nightly retention purge (`purge_expired`) do not crash on PostgreSQL.
2. **[P0] Fix `User.totp_secret` key rotation in `scripts/rotate_encryption_key.py` and guard `decrypt(user.totp_secret)` in `app/api/auth.py`** so 2FA users are not locked out on key rotation and recovery codes always work.
3. **[P1] Add missing `MSG91_*` and `DIGIO_*` env mappings to `docker-compose.prod.yml` (`&api-env`)** and add `ANTHROPIC_*` / `SENTRY_DSN` to `rtn-worker` in `render.yaml`.
4. **[P1] Add DPDP self-service buttons (Export Data, Delete Account, Delete Session, Withdraw Consent) to `frontend/components/AccountView.tsx` and `Home.tsx`** so the UI matches the promises in `docs/COMPLIANCE.md`.

### 9.2 Infrastructure & Third-Party Blockers (Require Owner Action)
1. **Data Residency Note on `render.yaml`:** `render.yaml` specifies `region: singapore` (Render's closest region to India). If strict Indian soil residency (`ap-south-1` Mumbai) is required for DPDP/government partnership, deploy PostgreSQL on Neon Mumbai (`aws-ap-south-1`), Supabase Mumbai, or AWS RDS `ap-south-1` (`infra/terraform/main.tf` already defaults to `ap-south-1`).
2. **Real Integration Credentials (`INTEGRATIONS_MODE=real`):** Requires SMTP (Brevo/SES), MSG91 (DLT registration), and Digio (eSign/DigiLocker aggregator contract). Note: The application can launch in **Assisted / Public Beta mode** with `INTEGRATIONS_MODE=mock` + real `SMTP_*` while DLT and Digio onboarding complete.

---

## 10. Exact Environment-Variable Checklist

### 10.1 Backend (`backend` API & `arq` Worker)
| Variable | Required in Prod? | Default | Purpose & Validation Rules (`app/core/config.py`) |
|---|---|---|---|
| `ENV` | **Yes** | `dev` | Set to `prod`. Triggers strict startup validation (`validate_for_Startup()`). |
| `SECRET_KEY` | **Yes** | `dev-only-...` | JWT HMAC signing key (`HS256`). Must be ≥ 32 chars (`openssl rand -hex 32`) and not start with `dev-only`. |
| `FIELD_ENCRYPTION_KEY` | **Yes** | `""` | URL-safe base64 32-byte Fernet key for encrypting Aadhaar/PAN/bank/TOTP secrets at rest. |
| `FIELD_ENCRYPTION_KEY_PREVIOUS` | No | `""` | Comma-separated previous Fernet keys during key rotation window. |
| `DATABASE_URL` | **Yes** | `sqlite+aiosqlite:///./dev.db` | Must start with `postgresql+asyncpg://` in `ENV=prod`. |
| `REDIS_URL` | **Yes** (for worker) | `""` | `redis://...` or `rediss://...` for `RedisCache` and `arq` background queue. |
| `CORS_ORIGINS` | **Yes** | `["http://localhost:3000"]` | JSON array of allowed origins; cannot contain `*` or `localhost` in `ENV=prod`. |
| `PUBLIC_ORIGIN` | **Yes** | `http://localhost:3000` | Public HTTPS URL of the frontend (used in password reset, email verify, and workspace invite links). |
| `INTEGRATIONS_MODE` | **Yes** | `mock` | `mock` (safe simulated adapters) or `real` (enforces `DIGIO_*` and `MSG91_*` presence at startup). |
| `SMTP_HOST` | Recommended | `""` | SMTP server hostname (e.g., `smtp-relay.brevo.com`). When set, real email sending activates even if `INTEGRATIONS_MODE=mock`. |
| `SMTP_PORT` | Recommended | `587` | `587` (STARTTLS) or `465` (`SMTP_USE_SSL=true`). |
| `SMTP_USER` | Recommended | `""` | SMTP username. |
| `SMTP_PASSWORD` | Recommended | `""` | SMTP password / API key. |
| `SMTP_FROM` | Recommended | `"Red Tape Navigator <no-reply@redtapenavigator.in>"` | Verified sender address. |
| `SMTP_USE_TLS` / `SMTP_USE_SSL` | No | `true` / `false` | Transport encryption flags. |
| `MSG91_AUTHKEY` | If `INTEGRATIONS_MODE=real` | `""` | MSG91 API authentication key. |
| `MSG91_SENDER_ID` | If `INTEGRATIONS_MODE=real` | `"RTNAVI"` | 6-character DLT-approved sender header. |
| `MSG91_TEMPLATE_ID` | If `INTEGRATIONS_MODE=real` | `""` | DLT-approved Flow template ID. |
| `MSG91_TEXT_VAR` | No | `"var"` | Variable name inside the MSG91 DLT template. |
| `DIGIO_CLIENT_ID` | If `INTEGRATIONS_MODE=real` | `""` | Digio API client ID. |
| `DIGIO_CLIENT_SECRET` | If `INTEGRATIONS_MODE=real` | `""` | Digio API client secret. |
| `DIGIO_ENV` | If `INTEGRATIONS_MODE=real` | `"sandbox"` | `"sandbox"` (`ext.digio.in:444`) or `"production"` (`api.digio.in`). |
| `DIGIO_WEBHOOK_SECRET` | If `INTEGRATIONS_MODE=real` | `""` | Shared secret to verify `X-Digio-Checksum` HMAC-SHA256 signatures on `/api/v1/webhooks/digio`. |
| `DIGIO_WEBHOOK_IPS` | No | `""` | Optional comma-separated IP/CIDR allowlist for Digio webhooks. |
| `DIGIO_DIGILOCKER_TEMPLATE` | No | `"DEFAULT"` | Digio KYC template name requesting Aadhaar/PAN/GST docs. |
| `ANTHROPIC_API_KEY` | No (Optional) | `""` | Optional Claude API key for free-text intake fallback & grounded research synthesis. |
| `ANTHROPIC_MODEL` | No (Optional) | `""` | E.g., `claude-haiku-4-5-20251001`. Leave empty to run 100% deterministically at ₹0 LLM cost. |
| `SENTRY_DSN` | No (Optional) | `""` | Sentry DSN for unhandled exception reporting (`send_default_pii=False`). |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | No (Optional) | `""` | OpenTelemetry HTTP collector URL (e.g., `https://otel.example.com/v1/traces`). |
| `OTEL_SERVICE_NAME` | No | `"red-tape-navigator"` | Service identifier in OTel spans. |
| `ACCESS_TOKEN_TTL_MIN` | No | `60` | Access JWT lifetime in minutes. |
| `REFRESH_TOKEN_TTL_DAYS` | No | `30` | Refresh token lifetime in days. |
| `RETENTION_DAYS` | No | `180` | Days after which inactive sessions are purged by `purge_expired`. |
| `RATE_LIMIT_PER_MIN` | No | `120` | General API requests per minute per IP. |
| `AUTH_RATE_LIMIT_PER_MIN` | No | `20` | `/api/v1/auth/*` requests per minute per IP. |

### 10.2 Frontend (`frontend` Next.js Build & Runtime)
| Variable | Required in Prod? | Default | Purpose |
|---|---|---|---|
| `NEXT_PUBLIC_API_BASE` | **Yes** (Build-time) | `/api/v1` | Baked into client JS bundle at `next build` time. Set to `/api/v1` when behind Caddy/Vercel rewrite, or `https://your-api.onrender.com/api/v1` for cross-origin. |
| `BACKEND_ORIGIN` | If using Next.js proxy | `http://localhost:8000` | Used by `frontend/next.config.mjs` `rewrites()` when proxying `/api/v1/*` through Next.js. |

---

## 11. Test Results (Actual Executed Runs)

All quality checks below were executed directly in `d:\Hack_N_Pitch\Red_Tape_Navigator` during this audit:

| Check Suite | Command Executed | Status | Actual Output & Metrics |
|---|---|---|---|
| **Backend Lint** | `ruff check .` | **PASS** | `All checks passed!` (0 warnings, 0 errors across `app/`, `tests/`, `evals/`) |
| **Backend Type Check** | `mypy app` | **PASS** | `Success: no issues found in 81 source files` |
| **Backend Test Suite & Coverage** | `python -m pytest -q` | **PASS** | **`453 passed in 238.90s (0:03:58)`** (0 failed, 0 skipped) — Total line coverage: **`95.78%`** (exceeds 80.0% gate; `free_forever` check passed) |
| **AI Evaluation Suite** | `python -m evals.run` | **PASS** | `cases: 26, passed: 26, pass_rate: 1.0, citation_coverage: 1.0, claims_checked: 600, hallucinations: 0, mean_precision: 1.0, mean_recall: 1.0, gates_passed: true` |
| **Rule Freshness Gate** | `python ../scripts/rule_freshness.py --strict` | **PASS** | `rules: 438, ok: 438, warn(>60d): 0, overdue(>90d): 0` (exit code 0) |
| **Frontend Lint** | `npm run lint` (`eslint . --max-warnings 0`) | **PASS** | 0 errors, 0 warnings |
| **Frontend Type Check** | `npm run typecheck` (`tsc --noEmit`) | **PASS** | 0 type errors |
| **Frontend Unit Tests** | `npm test` (`vitest run`) | **PASS** | `1 passed (1)` — `tests/messages.test.ts` (`7 passed` in 19ms; verified `en`/`hi`/`bn` key & placeholder parity, DPDP privacy keys, and `api.ts` helpers) |
| **Frontend Production Build** | `npm run build` (`next build`) | **PASS** | Compiled cleanly; 30 static routes generated (`/[locale]`, `/account`, `/invite`, `/privacy`, `/terms`, `/reset`, `/staff`, `/teams`, `/verify-email` across `en`/`hi`/`bn`) + dynamic `/[locale]/session/[id]` |

---

## 12. Recommended Implementation Order (P0 → P3)

### `P0` — Critical Security, Compliance & Data-Loss Fixes (Immediate)
1. **Task P0-1: Fix DPDP Erasure & Key Rotation Data-Loss Bugs + Deployment Env Parity**
   - Fix `app/services/privacy.py:_delete_session_data` to delete `ExternalRequest` rows before deleting `NavSession`, and add an Alembic migration `0008` (or explicit delete + SQLite FK pragma in tests) to prevent FK crashes on PostgreSQL.
   - Fix `scripts/rotate_encryption_key.py` to also rotate `User.totp_secret`, and harden `app/api/auth.py:_consume_second_factor` so `InvalidToken` on `totp_secret` does not block backup recovery codes.
   - Add `"bank_account_number"` and `"ifsc"` to `app/core/crypto.py:SENSITIVE_KEYS`.
   - Add missing `MSG91_*` and `DIGIO_*` env vars to `docker-compose.prod.yml` and `ANTHROPIC_*` / `SENTRY_DSN` to `rtn-worker` in `render.yaml`.

### `P1` — Required for Functional & Compliant Production Product
2. **Task P1-1: Citizen DPDP Self-Service UI & Session Clarify Fix**
   - Add "Export My Data (JSON)", "Withdraw Consent", and "Delete My Account" controls to [`frontend/components/AccountView.tsx`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/frontend/components/AccountView.tsx) and per-session delete buttons in [`frontend/components/Home.tsx`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/frontend/components/Home.tsx) (`en`/`hi`/`bn`).
   - Fix [`frontend/components/SessionView.tsx`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/frontend/components/SessionView.tsx) clarify form to reset `answer` state on submit, disable button while busy, and display API errors.
3. **Task P1-2: Audit Chain Concurrency Safety, Redis-Backed Rate Limiting & 2FA Brute-Force Protection**
   - Serialize `app/core/audit.py:record()` writes (or use row-level lock / retry) so concurrent requests cannot fork the hash chain.
   - Back `RateLimiter` in `app/core/middleware.py` with Redis (`app/core/cache.py`) and bound the fallback in-memory dictionary size.
   - Increment `user.failed_logins` on failed `/auth/2fa/enable` and `/auth/2fa/disable` attempts.
   - Add `sentry-sdk>=2.0.0` to `backend/pyproject.toml`.
4. **Task P1-3: Gemini API Provider Support & Digio DigiLocker Field Mapping**
   - Done: Gemini support alongside Anthropic and Ollama, with the zero-cost deterministic fallback preserved.
   - Implement document field extraction (`full_name`, `dob`, `address`, `aadhaar`, `pan`, `gstin`) in `DigioDigiLocker.get_status()` (`app/integrations/real/digio.py`) with comprehensive unit tests.
5. **Task P1-4: Staff Console Completion**
   - Extend [`frontend/components/StaffConsole.tsx`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/frontend/components/StaffConsole.tsx) with tabs for Rule Freshness (`GET /admin/rule-freshness`), Audit Chain Verification (`GET /admin/audit/verify`), User Role Assignment (`POST /admin/users/{id}/role`), and Expired Session Purge (`POST /admin/purge`).

### `P2` — Important Product Improvements
6. **Task P2-1: Renewal `.ics` Calendar Export & Printable Checklist**
   - Add `.ics` file download in [`DoneView.tsx`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/frontend/components/DoneView.tsx) for licence renewal dates and improve `@media print` styles.
7. **Task P2-2: Citizen Document Vault (Supporting Attachments)**
   - Allow citizens to upload and manage supporting documents (PDF/JPG/PNG ≤ 5 MB, magic-byte validated, encrypted at rest) mapped to checklist requirements.
8. **Task P2-3: SEO (`sitemap.ts`, `robots.ts`, OpenGraph) & PWA (`manifest.webmanifest`)**
   - Add Next.js metadata, `sitemap.ts`, `robots.ts`, and PWA web manifest for mobile installability.

### `P3` — Optional Enhancements
9. **Task P3-1: Partner Portal for CAs / CSCs (`/partner`)**
   - Dedicated multi-client compliance table and bulk renewal calendar built on top of `workspaces`.
10. **Task P3-2: Help Centre & Citizen Support FAQ (`/help`)**
    - Localized (`en`/`hi`/`bn`) FAQ and grieving/support contact page.

---

## 13. Human-Only Actions

The following actions cannot be automated by code and must be performed by the project owner / legal entity before full production launch (see also `docs/OWNER_ACTIONS.md` and `docs/HUMAN_TODO.md`):

1. **Domain & DNS Setup:** Register production domain (e.g., `redtapenavigator.in`) and point `A`/`CNAME` records to hosting providers (Vercel + Render or VPS with Caddy).
2. **Generate Production Secrets:** Generate `SECRET_KEY` (`openssl rand -hex 32`) and `FIELD_ENCRYPTION_KEY` (Fernet 32-byte base64 key) and store `FIELD_ENCRYPTION_KEY` in an offline password manager/vault (losing it makes encrypted PII unrecoverable).
3. **Provision Managed PostgreSQL 16 (with `pgvector`) & Redis 7:** Preferably in an Indian region (`ap-south-1` Mumbai) to satisfy DPDP data localization expectations.
4. **SMTP Provider Setup (Brevo / AWS SES):** Create account, verify domain SPF/DKIM/DMARC records, and set `SMTP_*` environment variables.
5. **TRAI DLT Registration & MSG91 Setup (for real SMS):** Register Principal Entity on a telecom DLT portal (Jio/Airtel/Vi), register 6-char sender header (`RTNAVI`), get the reminder SMS template approved, and configure `MSG91_*`.
6. **Digio Aggregator Onboarding (for real Aadhaar eSign & DigiLocker):** Execute contract + KYC with Digio (`https://www.digio.in`), test in sandbox (`DIGIO_ENV=sandbox`), register webhook URL (`https://<api-domain>/api/v1/webhooks/digio`), and switch to `DIGIO_ENV=production`.
7. **Legal Review of Privacy Notice, Terms & Disclaimer:** Have an Indian technology/regulatory counsel review `frontend/messages/{en,hi,bn}.json` (`legal.*`) and appoint a named **Grievance Officer** (`grievance@redtapenavigator.in`) as required under DPDP Act 2023 §8(10).
8. **Bootstrap Initial Admin & Reviewer Accounts:** Run `python -m scripts.create_admin --email <you> --password <strong-pw> --role admin` on the production database and immediately enable TOTP 2FA from the Account sheet.
9. **Verify Official Government Form PDFs:** From `/staff`, click `Fetch` -> inspect SHA-256 & layout -> `Activate` for each licence that has an `official_form_url`.

---

## 14. Final Production Readiness Assessment

### 14.1 Overall Verdict: **READY FOR STAGING / ASSISTED LAUNCH (Code P0 & P1 Privacy/UX/Security Blockers + P2 Document Vault + Provider Readiness Resolved)**
- **Engineering Quality:** The repository now passes **470 backend tests (95.17% coverage, 0 failed, 0 skipped)**, **9/9 frontend unit tests**, **100% pass rate on the 26-case AI evaluation suite with 0 hallucinations across 600 claims**, **438 fresh verified regulatory rules**, strict `ruff`/`mypy`/`eslint`/`tsc` checks, and complete English/Hindi/Bengali localization.
- **Completed P0 & P1 Remediations (2026-11-12):**
  1. **[RESOLVED — P0]** Fixed `ExternalRequest` foreign-key deletion order in `backend/app/services/privacy.py` and added non-destructive Alembic migration `0008_external_requests_cascade.py` (`ON DELETE CASCADE` on `external_requests.session_id`).
  2. **[RESOLVED — P0]** Updated `scripts/rotate_encryption_key.py` to rotate encrypted `User.totp_secret` alongside sensitive `Answer` rows, and hardened `backend/app/api/auth.py` (`_consume_second_factor` and `two_factor_enable`) so undecryptable/corrupted TOTP secrets log a safe warning (`totp_secret_decrypt_failed`) and fall through to recovery codes without HTTP 500.
  3. **[RESOLVED — P1]** Expanded `SENSITIVE_KEYS` in `backend/app/core/crypto.py` to redact `bank_account_number`, `bank_ifsc`, `ifsc`, and `totp_secret`.
  4. **[RESOLVED — P1]** Added missing `MSG91_*` and `DIGIO_*` environment variables to `docker-compose.prod.yml` and `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, and `SENTRY_DSN` to `rtn-worker` in `render.yaml`.
  5. **[RESOLVED — P1]** Implemented complete DPDP self-service UI in `frontend/components/AccountView.tsx` and `frontend/components/Home.tsx` (`Export My Data`, `Consent Management`, `Delete Session Data`, and `Delete My Account` with `DELETE` confirmation phrase and token cleanup) across `en`, `hi`, and `bn`.
  6. **[RESOLVED — P1]** Fixed multi-step clarification UX in `frontend/components/SessionView.tsx` (clears input on success, preserves input on failure, prevents duplicate submissions with `clarifyBusy`, and renders accessible error alerts).
  7. **[RESOLVED — P1]** Hardened audit-chain concurrency in `backend/app/core/audit.py` using PostgreSQL transaction-level advisory locking (`pg_advisory_xact_lock(748291041)`) + `SELECT ... FOR UPDATE` and per-event-loop `asyncio.Lock` (`WeakKeyDictionary`) so concurrent writes across multiple workers cannot fork `prev_hash`.
  8. **[RESOLVED — P1]** Implemented Redis-backed rate limiting in `backend/app/core/middleware.py` (`RateLimiter.allow_async`) using atomic `MULTI`/`EXEC` `INCR` + `EXPIRE` pipelines with a cached Redis client, failing open safely to a bounded 10,000-key in-memory sliding window with regular expired-entry eviction.
  9. **[RESOLVED — P1]** Enforced consistent 2FA brute-force protection and account lockout (`_enforce_not_locked` and `_record_failed_attempt`) across `/auth/login`, `/auth/2fa/enable`, and `/auth/2fa/disable` in `backend/app/api/auth.py`, resetting counters on success and never leaking whether TOTP or recovery code failed.
   - **[RESOLVED — P2]** Implemented Citizen Document Vault & Object Storage Abstraction (`backend/app/core/storage.py`, `backend/app/core/scanner.py`, `backend/app/api/documents.py`, migration `0009_document_vault.py`, `frontend/components/DocumentsView.tsx`, and `/[locale]/documents`): supports `STORAGE_BACKEND=local|s3` (AWS SigV4), 5 MB cap, PDF/PNG/JPEG allowlist + magic-byte verification, opaque storage keys, pluggable malware-scanner hook (`DOCUMENT_SCAN_MODE=disabled|external`), DPDP session/account deletion cleanup, and full `en`/`hi`/`bn` UI.
- **Remaining Blockers Before Live Production Deployment:**
  - Owner/External onboarding: production domain & TLS, `SECRET_KEY` and `FIELD_ENCRYPTION_KEY` generation, managed PostgreSQL 16 (`pgvector`) + Redis 7 provisioning, SMTP sender verification, MSG91 TRAI DLT registration, Digio sandbox/production credentials + DigiLocker response field mapping, and legal counsel review of DPDP notice & Grievance Officer contact.

---

## 15. First Implementation Task Specification (Task P0-1)

Per Step 7 of the audit instructions, below is the exact specification for the **FIRST implementation task** (do not execute until approved):

### Task Title
**Task P0-1: Fix PostgreSQL DPDP Erasure Foreign-Key Crash, 2FA Encryption Key Rotation Lockout, PII Redaction Gap, and Production Env Parity**

### 1. Exact Files to Modify
1. [`backend/app/services/privacy.py`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/backend/app/services/privacy.py)
2. [`backend/app/api/auth.py`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/backend/app/api/auth.py)
3. [`scripts/rotate_encryption_key.py`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/scripts/rotate_encryption_key.py)
4. [`backend/app/core/crypto.py`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/backend/app/core/crypto.py)
5. [`docker-compose.prod.yml`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/docker-compose.prod.yml)
6. [`render.yaml`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/render.yaml)
7. [`backend/tests/test_privacy_and_admin.py`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/backend/tests/test_privacy_and_admin.py)
8. [`backend/tests/test_totp_2fa.py`](file:///d:/Hack_N_Pitch/Red_Tape_Navigator/backend/tests/test_totp_2fa.py)

### 2. Proposed Changes
- **`backend/app/services/privacy.py`:**
  - Import `ExternalRequest` from `app.db.models`.
  - In `_delete_session_data(db, session_ids)`, execute `await db.execute(delete(ExternalRequest).where(ExternalRequest.session_id.in_(session_ids)))` prior to `delete(NavSession)`.
  - In `delete_account(db, user_id)`, also execute `await db.execute(delete(ExternalRequest).where(ExternalRequest.user_id == user_id))` to catch any orphaned external requests.
- **`scripts/rotate_encryption_key.py`:**
  - Import `User` from `app.db.models`.
  - After rotating sensitive `Answer` rows, query `select(User).where(User.totp_secret.is_not(None))` and re-encrypt each non-empty `user.totp_secret` via `encrypt(decrypt(u.totp_secret))`, returning both counts `{"answers_rotated": ..., "totp_secrets_rotated": ...}`.
- **`backend/app/api/auth.py`:**
  - In `_consume_second_factor(user, code)`, wrap `decrypt(user.totp_secret)` in `try ... except Exception:` (catching `InvalidToken`) so that a corrupted/unrotated `totp_secret` logs a warning and falls through cleanly to check `user.recovery_hashes` instead of raising an unhandled 500 error.
  - In `disable_2fa`, also increment `user.failed_logins` (and apply lockout threshold) when an invalid 2FA code is submitted.
- **`backend/app/core/crypto.py`:**
  - Expand `SENSITIVE_KEYS` on line 10 to `{"aadhaar", "pan", "aadhaar_number", "pan_number", "bank_account_number", "ifsc"}`.
- **`docker-compose.prod.yml` & `render.yaml`:**
  - Add `MSG91_AUTHKEY`, `MSG91_SENDER_ID`, `MSG91_TEMPLATE_ID`, `MSG91_TEXT_VAR`, `DIGIO_CLIENT_ID`, `DIGIO_CLIENT_SECRET`, `DIGIO_ENV`, `DIGIO_WEBHOOK_SECRET`, `DIGIO_WEBHOOK_IPS`, and `DIGIO_DIGILOCKER_TEMPLATE` to `&api-env` in `docker-compose.prod.yml`.
  - Add `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, and `SENTRY_DSN` to `rtn-worker` in `render.yaml`.

### 3. Dependencies
- None (uses existing `sqlalchemy`, `cryptography`, and `pytest` packages already installed).

### 4. Tests Required
- **Test 1 (`tests/test_privacy_and_admin.py`):** Enable SQLite foreign keys (`PRAGMA foreign_keys=ON`) in test setup or create an `ExternalRequest` linked to a session (via DigiLocker/eSign start), then call `DELETE /api/v1/privacy/sessions/{sid}` and `DELETE /api/v1/privacy/me`, asserting HTTP 200 and zero remaining `ExternalRequest` rows.
- **Test 2 (`tests/test_totp_2fa.py`):** Enable 2FA for a user, rotate `FIELD_ENCRYPTION_KEY` using `rotate_encryption_key.rotate()`, remove the old key, and verify that both TOTP login and recovery-code login succeed. Also test that if `user.totp_secret` contains undecryptable ciphertext, logging in with a valid recovery code still succeeds (HTTP 200 instead of HTTP 500).
- **Test 3 (`tests/test_Security_and_ops.py`):** Verify `crypto.redact({"bank_account_number": "123456789012"})` masks the value as `"***REDACTED***"`.

### 5. Acceptance Criteria
1. `DELETE /api/v1/privacy/sessions/{sid}`, `DELETE /api/v1/privacy/me`, and `POST /api/v1/admin/purge` succeed without `IntegrityError` when `external_requests` rows exist for the session, with foreign key enforcement enabled.
2. `scripts/rotate_encryption_key.py` rotates both `Answer.value` and `User.totp_secret`, and `_consume_second_factor` never raises an unhandled 500 if `totp_secret` decryption fails.
3. `crypto.redact()` redacts `bank_account_number` and `ifsc` keys.
4. `ruff check .`, `mypy app`, and `pytest -q` pass with ≥ 95% coverage.

---

## PART 13 — PRODUCT-LEVEL GAP AUDIT & WORKFLOW COMPLETION (2026-11-12)

### 1. Product Feature Classification
- **Already Implemented & Verified:**
  - Citizen registration, login, password reset, email verification, TOTP 2FA with single-use recovery codes, and brute-force lockout across login/enable/disable.
  - DPDP Consent Gate (`service`, `reminders`, `identity_providers`) and full self-service privacy controls (`Export My Data`, `Consent Management`, `Delete Session Data`, `Delete My Account`).
  - Goal intake (AI-assisted with deterministic rules fallback + voice input), single-question clarification, and citation-backed licence planner (`438` rules across `8` cities and national scope).
  - Adaptive interview engine with Fernet encryption for sensitive PII (`aadhaar`, `pan`, `bank_account_number`, `ifsc`) and skip/resume support.
  - Human review checkpoint (`GET/POST /sessions/{sid}/review`), PDF form preview/download, online portal key-in sheets, and human-controlled submission checklist.
  - Secure Document Vault (`POST/GET/DELETE /documents`, `GET /documents/{id}/download`, local + S3 storage backends, optional external malware scanner hook, and `/[locale]/documents` UI).
  - Team workspaces (`/[locale]/teams` and `/[locale]/invite`) with owner/admin/member RBAC and session sharing.
  - External provider resilience (Anthropic PII redaction + bounded retries/timeout, SMTP bounded transient retry, MSG91 + Digio timeout/malformed-response handling, webhook validation, and `GET /admin/readiness`).
- **Completed in Prompt 07 (Previously Partial / Missing MVP Product Workflows):**
  - **Session Lifecycle & Step Navigation (`backend/app/api/sessions.py`, `frontend/components/SessionView.tsx`, `frontend/components/Home.tsx`):**
    - Added `PATCH /sessions/{sid}` allowing session owners/workspace members to rename a session's display title while preserving parsed intake/plan data.
    - Enhanced `GET /sessions` to return `stage` and `workspace_id`, surfaced as stage badges on the Dashboard.
    - Fixed `FROM_TRACKER` in `SessionView.tsx` so sessions at the `review` stage reopen directly on the Review screen, added interactive step navigation (`Checklist` ↔ `Interview` ↔ `Review` ↔ `Submit`), and added friendly localized 404/retry cards.
  - **Reminders & Notifications UX (`backend/app/api/sessions.py`, `frontend/components/DoneView.tsx`):**
    - Added `GET /sessions/{sid}/reminders` and `DELETE /sessions/{sid}/reminders/{rid}` so citizens can inspect existing scheduled reminders when reopening a session, see live vs mock channel readiness (`live` vs `mock`), distinguish `Scheduled` vs `Dispatched to provider`, and cancel scheduled reminders.
  - **Help & Support Centre (`frontend/components/HelpView.tsx`, `frontend/app/[locale]/help/page.tsx`):**
    - Created localized (`en`/`hi`/`bn`), searchable Help & Support Centre covering Getting Started, Using Your Results (AI vs deterministic rules vs official sources), Privacy & Security (DPDP rights), Document Vault, Troubleshooting, and Grievance Officer escalation (reading live `/privacy/policy` configuration without inventing fake contact details).
  - **Officer Console Operational Readiness (`frontend/components/StaffConsole.tsx`):**
    - Surfaced `GET /admin/readiness` provider status matrix and confirmation-gated `POST /admin/purge` retention cleanup in `StaffConsole.tsx`.
- **Out of Scope / By Design:**
  - Payment/billing (permanently removed; project is 100% free).
  - Automated government portal submission or captcha/OTP solving (prohibited by safety & compliance architecture; citizen always submits directly).

---

## PART 14 — PRODUCTION OPERATIONS, BACKUP/RESTORE READINESS & DISASTER RECOVERY (2026-11-12)

### 1. Operations Gap Audit
- **Already Implemented:**
  - `/health` (liveness), `/ready` (readiness), `/metrics` (Prometheus metrics with optional `METRICS_TOKEN`), and `/admin/readiness` (staff operational readiness matrix).
  - Structured JSON logging via `structlog`, request correlation (`X-Request-ID`), OpenTelemetry tracing, optional Sentry hook (`SENTRY_DSN`), Redis-backed rate limiting & caching with in-process fallback, hash-chained audit logging, and `scripts/rotate_encryption_key.py`.
- **Newly Completed in Prompt 08:**
  - **Health / Liveness / Readiness Separation (`backend/app/main.py`, `backend/app/api/admin.py`):**
    - Exposed `/health` + `/health/live` (liveness) and `/ready` + `/health/ready` (readiness with DB check, non-blocking Redis degradation status, and `storage_warning` when `STORAGE_BACKEND=local` in `APP_ENV=prod`).
    - Added `storage.durable` and `storage.production_warning` to `/admin/readiness`.
  - **Expanded Secret & Binary Log Redaction (`backend/app/core/crypto.py`, `backend/app/core/errors.py`):**
    - Expanded `SENSITIVE_KEYS` to redact passwords, API keys, JWT/refresh/reset tokens, encryption keys, webhook secrets, S3 secret keys, OTP/recovery codes, and raw binary/PDF fields (`[BINARY-REDACTED]`).
    - Added regex redaction in `redact_text()` for inline JWT tokens (`[JWT-REDACTED]`) and PostgreSQL connection string passwords (`postgresql://user:[REDACTED]@host/db`).
    - Ensured `capture_exception()` redacts context fields before logging.
  - **Database Backup & Non-Production Restore Verification Tooling (`scripts/db_backup_restore.py`):**
    - Implemented compressed timestamped `pg_dump` backup command builder and `pg_restore` verification workflow with `PGPASSWORD` subprocess isolation (never exposing passwords in CLI args or logs), `APP_ENV=prod` refusal, dual confirmation (`--confirm-non-prod-restore` + `CONFIRM_NON_PROD_RESTORE=YES_RESTORE_NON_PROD`), primary-DB collision refusal, production-marker refusal, required verification suffix (`_restore`, `_verify`, `_test`, `_scratch`, `_dr`), and post-restore SQL schema verification.
  - **Worker Observability (`backend/app/jobs/worker.py`):**
    - Wrapped Arq cron jobs (`refresh_rules`, `forms_job`, `purge_job`, `reminders_job`) in `_run_observed()` to emit `worker_job_started` / `worker_job_completed` logs and capture exceptions via `capture_exception()`.
  - **Deployment & Runbook Hardening (`docker-compose.prod.yml`, `render.yaml`, `docs/RUNBOOK.md`, `.gitignore`):**
    - Mounted persistent `vaultdata:/var/lib/rtn/vault` volume on both `api` and `worker` and added `/health/ready` healthcheck in `docker-compose.prod.yml`.
    - Updated `render.yaml` health check to `/health/ready` and synced storage/logging/OTEL env vars across `rtn-api` and `rtn-worker`.
    - Expanded `docs/RUNBOOK.md` with RPO/RTO recommendations, storage durability matrix, and 6 incident response playbooks.



