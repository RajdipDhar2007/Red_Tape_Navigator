# Threat model

Short on purpose. Controls and the OWASP mapping are in `docs/SECURITY.md`; this file says who might attack, what they want, and what is still open.

## What is worth protecting

| Asset | Where it lives | Why it matters |
|---|---|---|
| Aadhaar, PAN, bank account answers | `answers.value`, Fernet-encrypted | Identity theft if leaked |
| Other interview answers (name, address, phone) | `answers`, plain text in the database | Personal data under the DPDP Act |
| Passwords, two-factor secrets, recovery codes | bcrypt hashes; TOTP secret encrypted; recovery codes hashed | Account takeover |
| Access and refresh tokens | browser `sessionStorage` | Account takeover while valid |
| The rules knowledge base | `claims` | A wrong rule misleads every citizen |
| The audit log | `audit_log`, hash-chained | Evidence of who did what |
| `FIELD_ENCRYPTION_KEY`, `SECRET_KEY` | host environment only | Decrypts everything / forges any session |

## Who attacks, and how far they get

| Attacker | Attempt | What stops it | Left open |
|---|---|---|---|
| Anonymous internet user | Guess passwords | bcrypt, 5-attempt lockout, 20 requests a minute per address on `/auth`, constant-time login, optional two-factor | Rate limits are per instance; with several replicas put a limiter at the gateway |
| Anonymous internet user | Read someone else's session | Every session route checks the owner or team membership and answers 404 (tested) | none known |
| Signed-in citizen | Become an officer | Self-registration is always `citizen`; roles change only through an admin route, audited | none known |
| Signed-in citizen | Make the app fetch internal addresses (SSRF) | Outbound fetches only to an allowlist of official domains, https only, redirects re-checked | Add an egress firewall at the host |
| Malicious web page a citizen visits | Use the citizen's session (CSRF) | The API reads the token from an `Authorization` header, never a cookie, so another site cannot send it | none while tokens are not in cookies |
| Script injected into our own pages (XSS) | Steal tokens from `sessionStorage` | React escaping, Content-Security-Policy, no third-party scripts, tokens die with the tab, access tokens last 15 minutes, refresh tokens rotate and reuse revokes the family | **Open:** the CSP still allows inline scripts (Next.js needs a nonce set-up to drop it) and tokens are readable by script. See "Planned" below |
| A poisoned government page | Prompt-inject the model during a rules refresh | Allowlist, sanitiser, content wrapped as untrusted, the model has no tools that act, a claim is kept only if its quote appears on the page, and an officer reviews changes | A page that is itself wrong; that is why every rule stays "verify with the authority" until signed off |
| Someone with a database dump | Read Aadhaar or PAN | Encrypted with a key that is not in the database | Names, addresses and phone numbers are not encrypted: rely on the host's disk encryption and access control |
| Someone with the host account | Everything | Two-factor on the Render, Vercel and GitHub accounts; few people with access | **Open:** this is on the owner |
| Forged Digio webhook | Mark a document signed | HMAC checksum on the raw body, duplicate ids dropped | The IP allowlist can be spoofed and is only a second layer |
| An officer | Quietly change a rule | Every resolution is audited with a note; the chain shows tampering | A second reviewer for high-impact rules is a process decision |

## Planned, not built

1. **Tokens out of script reach.** Serve the API under the website's own domain (one parent domain, or a proxy route), keep the refresh token in an `HttpOnly; Secure; SameSite=Strict` cookie, keep the access token in memory only, and add a CSRF header check. Not done yet because the free hosting tier puts the site and the API on different domains, where browsers block such cookies, and a proxy would time out while a sleeping free instance wakes. Do this when a custom domain is bought.
2. **Nonce-based CSP** so `script-src` can drop `'unsafe-inline'`.
3. **Operator delegation:** a CSC operator acting for many citizens needs its own consent and audit design before any pilot with operators.
4. **Independent penetration test** before real citizens' identity numbers are stored.

## Checked on 2026-11-12 (automated, in the test suite)

Anonymous access refused on every private route; another user's session, reminders and calendar file answer 404; a calendar title cannot inject calendar properties; the first-officer environment variables cannot overwrite an existing password; no secret has a committed value in either Render Blueprint; production refuses to start with demo mode, dev secrets, SQLite, http origins or missing email settings.
