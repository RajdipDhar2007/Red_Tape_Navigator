# Architecture

Red Tape Navigator is a monorepo: `/backend` (FastAPI), `/frontend` (Next.js), `/infra` (Docker/Terraform),
`/docs`, `/scripts`.

```mermaid
flowchart LR
  U[Citizen / CSC operator] --> FE[Next.js frontend<br/>en / bn / hi]
  FE -->|REST + JWT| API[FastAPI API]
  API --> AUTH[Auth/RBAC + Consent + Audit]
  API --> ORCH[Session orchestrator]
  ORCH --> INTAKE[A. Goal intake]
  ORCH --> RES[B. Research agent<br/>Claude tool-use loop]
  ORCH --> PLAN[C. Checklist planner]
  ORCH --> INT[D. Interview engine + memory]
  ORCH --> FILL[E. Form filler]
  ORCH --> REV[F. Review checkpoint]
  ORCH --> FUP[G. Follow-up / reminders]
  RES --> GUARD[Domain allowlist + sanitizer]
  GUARD --> SCR[Scrapers: httpx/trafilatura, Playwright]
  RES --> KB[(Rules KB<br/>Postgres + pgvector)]
  INT --> MEM[(Session memory<br/>Postgres + Redis)]
  FILL --> REG[Form template registry<br/>JSON field maps]
  FILL --> PDF[PDF engine<br/>pypdf / PyMuPDF / reportlab]
  FUP --> JOBS[Arq worker + scheduler]
  API --> INTEG[Integration adapters<br/>mock + real stub]
  INTEG -.-> DL[DigiLocker]
  INTEG -.-> ES[Aadhaar e-Sign]
  INTEG -.-> WA[WhatsApp / SMS / Email]
  API --> OBS[Prometheus / OTel / structured logs]
```

## Key design rules

1. **No autonomous submission.** There is no adapter method or route that posts to a government portal.
   The final step produces PDFs + a checklist; the citizen performs submission. Enforced by tests
   (`tests/test_no_submission.py`) that scan the code for submit capability.
2. **No claim without a citation.** `Claim` requires `source_url`, `fetched_at`, `content_hash`; the DB
   column is NOT NULL and the evaluation harness fails on uncited claims.
3. **Scraped content is data.** Fetched text passes the sanitizer, is delimited in prompts, and the LLM has
   no tool that can act on it beyond constrained, allowlisted tools.
4. **Never guess values.** The form filler emits `missing`/`doubtful`/`unmapped` flags instead of defaults.
5. **Sensitive fields (Aadhaar, PAN) are Fernet-encrypted at rest and redacted in logs.**
6. **Graceful degradation.** Without an `ANTHROPIC_API_KEY` the agent falls back to a deterministic
   rules-pack (curated seed KB) so the demo works offline; this is labelled in the UI.

## Backend layout

```
backend/app/
  core/        config, security (JWT, crypto), logging, metrics, resilience (retry/circuit breaker), rate limit
  db/          async engine, models, session
  api/         routers: auth, consent, sessions, research, interview, forms, review, followup, admin, health
  agent/       llm client, tool loop, intake, research, planner, prompts
  scraping/    allowlist, fetcher, robots, sanitizer
  kb/          rules knowledge base, versioning, diffing, embeddings
  interview/   field catalogue, validators, engine, i18n questions
  forms/       registry, templates/*.json, pdf fill (acroform + overlay), report
  integrations/ interfaces, mock, real stubs
  followup/    reminders, notifiers
  jobs/        worker tasks (refresh, purge, reminders)
backend/evals/ golden cases + harness
```

## Data flow (happy path)

Goal text → intake parse (state/city) → research (KB hit or scrape) → claims with citations/confidence →
ordered checklist → union of form fields → interview (only missing) → fill PDFs + field report →
review UI (edit, consent) → download + submission checklist → reminders.

## Session state and the human gate

```mermaid
stateDiagram-v2
  [*] --> Goal: POST /sessions (needs consent)
  Goal --> Goal: clarify (only if city/state missing)
  Goal --> Research: parsed
  Research --> Checklist: plan with cited claims
  Checklist --> Interview: start
  Interview --> Interview: answer / skip / edit
  Interview --> Review: required fields answered (or skipped)
  Review --> Interview: edit invalidates review
  Review --> Submit: POST /review {confirm:true}  (explicit human consent)
  Submit --> [*]: citizen downloads, signs and submits ON THE PORTAL
```

Downloads, e-Sign and the submission checklist return `403 review_required` until the human confirms; any later edit
resets `reviewed_at`. There is no route or adapter method that submits to a government portal.

## Data model (PostgreSQL)

`users`, `refresh_tokens`, `consents`, `audit_log` (hash-chained, immutable), `nav_sessions`, `answers` (sensitive values
Fernet-encrypted), `claims` (versioned; `source_url`, `fetched_at`, `content_hash` NOT NULL; `embedding vector(256)`;
partial unique index → one current version per key), `source_snapshots` (change detection), `review_queue`, `reminders`.

## Agent behaviour

* **Deterministic first:** rules parse the goal and build the plan from a catalogue; the LLM only fills gaps (validated
  against the catalogue) and extracts claims from official pages (accepted only with a verbatim quote).
* **Confidence:** `base` by claim type, +0.1 when verified live, −0.4 if the quote is not grounded, capped for unverified
  seed data, decays with age; `< 0.6` → `needs_verification` + review queue + "Verify with the authority" in the UI.
* **Resilience:** retry with backoff + timeouts + circuit breakers around every LLM call and per-host scraper;
  degradation is explicit in the UI (research mode label).
* **Change detection:** each source URL's content hash is snapshotted; a changed hash flags dependent claims and queues
  review; a weekly job re-fetches all sources.

## Security

See [SECURITY.md](SECURITY.md). Compliance: [COMPLIANCE.md](COMPLIANCE.md).
