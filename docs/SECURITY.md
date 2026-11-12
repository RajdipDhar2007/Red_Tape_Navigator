# Security design and OWASP Top 10 (2021) review

Who attacks, what stops them and what is still open: `docs/THREAT_MODEL.md`.

## Trust boundaries
Browser ⇄ API (JWT) ⇄ DB / Redis. **Scraped web content is untrusted data** crossing into the LLM. The LLM output is
untrusted input to the rest of the system.

## OWASP Top 10 mapping

| # | Risk | Controls in this repo | Residual / TODO |
|---|---|---|---|
| A01 | Broken access control | RBAC (`citizen`, `csc_operator`, `reviewer`, `admin`); sessions are owner-scoped and return **404** for others (tested); review queue / admin routes require roles; self-registration is always `citizen`; role changes are admin-only and audited | CSC operator ⇄ citizen delegation model (operator acting for many citizens) needs a design before the pilot |
| A02 | Cryptographic failures | Aadhaar/PAN/bank account Fernet-encrypted at rest; key rotation via `MultiFernet` + script; bcrypt passwords; HS256 JWT secret from env (prod refuses dev secrets); HSTS; TLS terminates at the ingress | Move to a KMS/HSM-backed key; asymmetric JWT (RS256/OIDC) |
| A03 | Injection | SQLAlchemy parameterised queries only; Pydantic validation on every body; field validators; **prompt-injection defence** below; PDF values are written through PyMuPDF/reportlab APIs, never interpolated | |
| A04 | Insecure design | Human-in-the-loop by construction: no submit code path (test), download/e-sign gated on an explicit review consent that is **invalidated by any later edit**; threat model above | |
| A05 | Security misconfiguration | Secure defaults; CSP on API (`default-src 'none'`) and web; `X-Frame-Options`, `nosniff`, `Referrer-Policy`, `Permissions-Policy`; docs/OpenAPI disabled in prod; CORS allow-list; non-root containers; CI verifies non-root | Review Terraform/IaC in the real cloud account |
| A06 | Vulnerable components | `pip-audit`, `npm audit --audit-level=high`, Trivy (images), bandit + ruff security rules (SAST), gitleaks in CI, CodeQL (opt-in: needs code scanning enabled, see `.github/workflows/codeql.yml`); lockfiles committed; dependency bumps are manual (`make audit`), enable Dependabot deliberately if you want automated PRs | 6 moderate **dev-tooling** npm advisories remain (documented; not shipped) |
| A07 | Identification & auth failures | Rate limit on `/auth` (20/min/IP, shared in Redis when `REDIS_URL` is set, with bounded 10,000-key in-memory fallback); access tokens 15 min; **rotating refresh tokens with reuse detection** (reuse revokes the whole family); constant-cost verification; consistent account lockout (`lockout_threshold=5`, `lockout_minutes=15`) across `/auth/login`, `/auth/2fa/enable`, and `/auth/2fa/disable` | OIDC provider (the code is OIDC-ready via `OIDC_ISSUER/AUDIENCE`, but only HS256 local issuance is implemented) |
| A08 | Software & data integrity | Hash-chained, append-only audit log serialized across workers via PostgreSQL `pg_advisory_xact_lock` + `SELECT ... FOR UPDATE` (and per-loop `asyncio.Lock` in-process) with verification endpoint; claims carry content hashes; CI pinned actions by major version | Sign images (cosign), SLSA provenance |
| A09 | Logging & monitoring failures | Structured JSON logs with PII redaction (Aadhaar/PAN regex + sensitive keys); request ids; Prometheus metrics; OpenTelemetry spans (no PII); error-tracking hook (Sentry) | Alerting rules (see RUNBOOK) |
| A10 | SSRF | Outbound fetches only to an **allowlist of official domains enforced in code**; HTTPS only; no IP literals, credentials or odd ports; **redirects re-checked hop by hop**; response size cap; robots.txt respected; per-domain rate limit + circuit breaker | Egress firewall at the network layer as defence in depth |

## Prompt-injection defence (LLM + scraping)
1. Domain allowlist (`config/sources.yaml`) enforced in `assert_allowed`, independent of the model.
2. Scraped text goes through `sanitize` (control/bidi characters stripped, instruction-like phrases removed and flagged).
   Flagged pages are **not** sent to extraction.
3. Content is wrapped in `<untrusted_source>` tags and the system prompt states it is data only.
4. The model has no tool that acts on the world. Tool arguments are Pydantic-validated before any handler runs;
   unknown tools / bad args return an error string to the model, never raise.
5. **Grounding:** an extracted claim is accepted only if its `quote` appears verbatim in the fetched page. Ungrounded claims
   are dropped (tested). Claims need an allow-listed `source_url`, hash and timestamp or construction fails.
6. Structured outputs are validated with Pydantic; the intake result is further validated against the catalogue
   (an invented activity is rejected).
7. Interview answers (Aadhaar, PAN…) are never placed in any prompt.

## Authentication notes
Tokens are kept in `sessionStorage` in the demo UI (cleared when the tab closes). For production, front the API with a
BFF that stores tokens in `HttpOnly; Secure; SameSite=Strict` cookies, or use the OIDC provider's session handling.

Second factor (added 2026-11-10, hardened 2026-11-12): optional TOTP (RFC 6238) with a Fernet-encrypted secret (`User.totp_secret`, rotated alongside encrypted `Answer` values by `scripts/rotate_encryption_key.py`), a used time step can never be reused, recovery
codes are random, single-use and stored only as SHA-256 hashes, and a wrong code on `/auth/login`, `/auth/2fa/enable`, or `/auth/2fa/disable` counts towards the same account lockout (`failed_logins` -> `locked_until` after 5 failures for 15 minutes) as a wrong password, resetting to `0` on success.
If `User.totp_secret` cannot be decrypted (e.g., corrupted ciphertext), `_consume_second_factor` logs a PII-free warning (`totp_secret_decrypt_failed`) and falls through to recovery-code verification rather than raising HTTP 500.
Disabling 2FA requires a valid password and a valid TOTP or recovery code (checked only after password verification so an attacker without the password cannot burn recovery codes), and returns a uniform error message (`"Password or code is incorrect"`) without leaking which factor failed. Known limits: no trusted-device memory, and the dev UI keeps tokens in `sessionStorage` (see above).

## Audit-chain concurrency & Redis-backed rate limiting
- **Audit-chain serialization (`backend/app/core/audit.py`):** `audit.record()` serializes hash-chain appends across multiple backend workers on PostgreSQL using a transaction-level advisory lock (`SELECT pg_advisory_xact_lock(748291041)`) combined with `SELECT ... FOR UPDATE` on the latest `AuditLog` row (ensuring even genesis writes on an empty table cannot fork `prev_hash`), plus a per-event-loop `asyncio.Lock` (`WeakKeyDictionary`) for in-process async coroutine serialization on SQLite and PostgreSQL.
- **Redis-backed rate limiting with bounded fallback (`backend/app/core/middleware.py`):** When `REDIS_URL` is configured, `RateLimiter.allow_async()` reuses a cached async Redis client and executes an atomic `MULTI`/`EXEC` pipeline (`INCR` + `EXPIRE`) on time-windowed keys (`rtn:rl:{key}:{bucket}`) shared across all API workers. If Redis is not configured or is temporarily unreachable, it logs a PII-free warning (`rate_limiter_redis_unavailable`) and falls back seamlessly to a bounded in-memory sliding window (`max_keys = 10,000`) with regular expired-entry sweeps and oldest-key eviction.

## DPDP data erasure & retention safety
- Session deletion (`DELETE /privacy/sessions/{sid}`) and retention purge (`purge_expired`) delete child rows in strict dependency order (`Answer`, `Reminder`, `ReviewItem`, `ExternalRequest`, and session-linked `Document` metadata + object-storage blobs) before deleting `NavSession`, reinforced by `ON DELETE CASCADE` on `external_requests.session_id` (migration `0008`).
- Account erasure (`DELETE /privacy/me`) deletes all owned sessions and child records, deletes private `Document` rows and their underlying storage objects (while preserving shared workspace documents legitimately used by other workspace members and unlinking `user_id`), removes any remaining user-linked `ExternalRequest` and `Reminder` rows, safely hands over or cleans up `Workspace` memberships (`NavSession.workspace_id` and `Document.workspace_id` reset to `NULL` before deleting an empty solo workspace), revokes all `RefreshToken` rows, and anonymises the `User` row (`deleted-<id>@erased.invalid`) while preserving PII-free `Consent` and `AuditLog` legal records.

## Document Vault & upload security (`backend/app/api/documents.py`, `backend/app/core/storage.py`, `backend/app/core/scanner.py`)
- **Storage abstraction:** Raw document bytes are never stored in PostgreSQL. `backend/app/core/storage.py` provides `LocalStorageBackend` (`STORAGE_BACKEND=local`, default `./data/vault`) for local development/testing and `S3StorageBackend` (`STORAGE_BACKEND=s3`, AWS Signature Version 4 `AWS4-HMAC-SHA256` over `httpx`) for S3-compatible object storage (AWS S3, Cloudflare R2, MinIO).
- **Upload validation:** Only authenticated users may upload (`POST /documents`). Uploads are capped at `MAX_UPLOAD_BYTES` (default 5 MB) in both `HardeningMiddleware` and chunked stream reading (`_read_bounded_upload`). Only `application/pdf`, `image/png`, and `image/jpeg` are allowed, verified against Content-Type, file extension (`.pdf`, `.png`, `.jpg`, `.jpeg`), and file magic bytes (`%PDF-`, PNG signature, JPEG SOI/EOI markers). Empty files and double-extension executables (e.g., `invoice.pdf.exe`) are rejected.
- **Path-traversal & key safety:** Client filenames are sanitized for display only (`sanitize_filename`) and never used in storage paths. Storage keys are opaque and server-generated (`vault/<user_id>/<uuid>.<ext>`), validated against `^vault/[A-Za-z0-9_-]{1,64}/[A-Za-z0-9_-]{1,64}\.(pdf|png|jpg)$`, and verified via `.resolve().is_relative_to(self.root)` in `LocalStorageBackend`. Failed or aborted writes clean up `.part-*` temporary files and delete orphaned storage objects if the database commit fails.
- **Malware-scanning hook (`backend/app/core/scanner.py`):** Configured via `DOCUMENT_SCAN_MODE=disabled|external` (`DOCUMENT_SCAN_URL`). When `disabled` (default), uploads are marked `scan_status="disabled"` and the UI/docs explicitly state that external antivirus scanning is not active. When `external`, uploads are POSTed to the configured scanner endpoint before storage; infected payloads are rejected with HTTP 422 (`malware_detected`) and scanner outages fail closed with HTTP 503 (`scanner_unavailable`).
- **Access control & download hardening:** `GET /documents/{id}` and `GET /documents/{id}/download` enforce owner or workspace-member authorization (returning `404` to unauthorized users) and serve files with `Content-Disposition: attachment` and `X-Content-Type-Options: nosniff`. Document bytes are never logged.

Teams: a session is visible to other people only when its owner shares it into a workspace; non-members get 404. Invitation tokens are
random, shown once, stored hashed, bound to one email address that must be confirmed, and expire after 7 days. Nothing is e-mailed on a
user's behalf.

## Reporting
Report vulnerabilities privately to the repository owner. Do not include real Aadhaar/PAN numbers in reports.

## Provider webhooks (Digio)
`POST /webhooks/digio` accepts only requests whose `X-Digio-Checksum` equals HMAC-SHA256(raw body, `DIGIO_WEBHOOK_SECRET`)
(constant-time compare); the secret is mandatory in production when Digio credentials exist. Optional source-IP allowlist
(`DIGIO_WEBHOOK_IPS`, only effective with `TRUST_PROXY=true`; the first `X-Forwarded-For` hop can be forged, so the checksum is the
real control). Deliveries are de-duplicated by webhook id, bodies over 1 MB are refused, nothing from the payload is logged
beyond status and error codes, and a late "partial" event never reopens a finished request. Documents are sent to Digio only after
the citizen's `identity_providers` consent and are never stored by us after signing (the signed PDF is fetched from Digio on demand).
