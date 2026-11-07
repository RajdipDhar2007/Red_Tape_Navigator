# Assumptions

Decisions made without asking, so work could continue end to end. Revisit before a pilot.

## Environment and tooling
- The development machine had Python 3.13 (the 3.12 install was broken); code targets Python 3.12 (Docker and CI use 3.12).
- Tests run on SQLite (aiosqlite) so they need no services; CI additionally runs the whole suite plus Alembic
  upgrade/downgrade on PostgreSQL 16 + pgvector. Production uses PostgreSQL + pgvector + Redis.
- Job runner: **Arq** (Redis, async-native). Weekly source refresh, daily retention purge, half-hourly reminders.
- Embeddings: a dependency-free hashing embedding (256 dims) so the KB works without an embedding API; the column is
  `vector(256)` on PostgreSQL and search is hybrid (vector + keyword). Swap `kb/embedding.py` for a real model later.
- Local Docker was not running on the development machine, so the container stack was verified in CI
  (`compose-smoke` job) instead of locally.
- The repository is private. CodeQL is opt-in (code scanning is not enabled on the private repo); bandit/ruff provide SAST.

## Data and content
- **The rules knowledge base is a curated seed pack** (`backend/app/kb/catalog.py`) with real official source URLs, not
  a copy of the law. Fees and timelines are indicative; municipal fees are deliberately left as "varies, confirm with
  the authority" with low confidence so they are flagged. Everything must be verified by a domain expert before a pilot.
- Coverage: 11 activities (bakery, restaurant, cafe, tea stall, cloud kitchen, sweet shop, home food, grocery,
  tailoring, beauty parlour, small manufacturing) x 8 cities (Kolkata, Mumbai, Delhi, Bengaluru, Chennai, Hyderabad,
  Pune, Ahmedabad). Other cities get national licences plus an explicit "no municipal data, a human has been notified" flag.
- Dependency order between licences (Udyam -> FSSAI -> trade licence -> fire NOC / shops & establishment) is a
  reasonable default; actual sequencing varies by city and must be confirmed.
- Real government form PDFs could not be fetched/redistributed offline. The three templates (FSSAI Form A, Udyam
  details sheet, municipal trade licence) use **clearly marked placeholder PDFs**; JSON field maps are real and
  documented so the official PDFs can be dropped in (docs/INTEGRATIONS.md).
- Without `ANTHROPIC_API_KEY` + `ANTHROPIC_MODEL` the system uses deterministic rules for intake/research and says so in
  the UI ("rules_fallback", research mode label). The LLM code paths are tested with fakes, not against the live API.
- Live scraping of portals was not exercised against real sites (no network guarantees in CI). The fetcher, robots,
  allowlist, redirect re-checks and change detection are unit-tested with fakes.

## Product and policy
- Self-registered users are always `citizen`; elevated roles are granted by an admin.
- An applicant must be 18+ (date-of-birth validator).
- Aadhaar numbers are stored (encrypted) only because the chosen forms ask for them. A masked/virtual-ID flow may be
  preferable; needs legal sign-off.
- Default retention is 90 days (`RETENTION_DAYS`); consent log and PII-free audit log are retained as legal records.
- "Skip for now" lets the user reach review with gaps; review then requires an explicit acknowledgement that the
  missing fields will be filled by hand.
- All integrations default to labelled mocks. DigiLocker mock import is only available in demo mode.
- Tokens are kept in `sessionStorage` in the demo UI; production should use an HttpOnly-cookie BFF (docs/SECURITY.md).
- JWTs are locally issued HS256. The code is "OIDC-ready" through config but external OIDC verification is not implemented.
