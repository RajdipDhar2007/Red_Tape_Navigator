# Security design and OWASP Top 10 (2021) review

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
| A06 | Vulnerable components | `pip-audit`, `npm audit --audit-level=high`, Trivy (images), CodeQL, Dependabot-style updates; lockfiles committed | 6 moderate **dev-tooling** npm advisories remain (documented; not shipped) |
| A07 | Identification & auth failures | Rate limit on `/auth` (20/min/IP); access tokens 15 min; **rotating refresh tokens with reuse detection** (reuse revokes the whole family); constant-cost verification | MFA, OIDC provider (the code is OIDC-ready via `OIDC_ISSUER/AUDIENCE`, but only HS256 local issuance is implemented) |
| A08 | Software & data integrity | Hash-chained, append-only audit log with verification endpoint; claims carry content hashes; CI pinned actions by major version | Sign images (cosign), SLSA provenance |
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

## Reporting
Report vulnerabilities privately to the repository owner. Do not include real Aadhaar/PAN numbers in reports.
