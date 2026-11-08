# Red Tape Navigator

An agentic assistant that helps Indian citizens and small-business owners navigate government bureaucracy.
Say your goal in plain language ("I want to open a small bakery in Kolkata"). The agent researches the rules from
official sources, asks **only** for the details that are missing, fills the official forms, and shows everything for
review. **The citizen reviews, signs and submits. The system never submits anything on its own.**

> AI-assisted guidance, not legal advice. Verify with the issuing authority.

## Quick start

Prerequisites: Docker (with Compose). For local development without Docker: Python 3.12+, Node 22+.

```bash
make setup     # installs deps, creates .env from .env.example
make dev       # db + redis + api + worker + web  ->  http://localhost:3000
```

Open <http://localhost:3000>, click **Use a demo account**, accept the data notice, then **Try the demo: bakery in
Kolkata**. The demo runs end to end: goal → research → checklist → interview → filled PDFs → review → download.
(The full 5-minute walkthrough is in [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md).)

Without Docker (SQLite, no Redis, no LLM key needed):

```bash
cd backend && python -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
uvicorn app.main:app --reload            # API on :8000 (docs at /docs in dev)
cd ../frontend && npm install && npm run dev   # UI on :3000
```

| Command | What it does |
|---|---|
| `make setup` / `make dev` / `make stop` | install / run whole stack / stop |
| `make test` | backend pytest (**≥ 80 % coverage enforced**) + frontend unit tests |
| `make lint` | ruff, mypy, eslint, tsc |
| `make eval` | golden cases, citation coverage, hallucination gate |
| `make e2e` | Playwright end-to-end (goal → interview → PDF → review) |
| `make smoke` | run the demo scenario through the API of a running stack (CI runs it against the real compose stack) |
| `make migrate` / `make seed` | Alembic migrations / load curated rules pack |
| `make audit` | pip-audit, bandit, npm audit |
| `make loadtest` | Locust ([baseline](docs/LOAD_TEST.md)) |

## What is real and what is mocked

| Area | Status |
|---|---|
| Goal intake (rules + optional Claude), research agent, rules KB with citations / confidence / versioning / diffing | **Built.** Works offline on the curated seed pack; live verification + LLM extraction activate with `ANTHROPIC_API_KEY` + `ANTHROPIC_MODEL`. |
| Seed rules pack (licences, fees, timelines for 11 activities × 8 cities) | **Seed data, not law.** Every claim carries a source URL and is flagged "verify with the authority" when confidence is low. Must be verified against live sources before a pilot. |
| Interview engine, validators (PAN, Aadhaar Verhoeff, PIN, mobile, IFSC, dates), encrypted memory, skip/resume/edit | **Built.** en / bn / hi. |
| Form filler (AcroForm + flat-PDF overlay), 3 templates, field-by-field provenance report | **Built**, but the PDFs are **clearly marked placeholders**. Adding the real forms: [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md). |
| Review UI, explicit consent gate, downloads, submission checklist, reminders | **Built.** |
| DigiLocker, Aadhaar e-Sign, UMANG, WhatsApp / SMS / email | **Mocked** and labelled in the UI ("Demo mode: simulated …"). Real adapters are stubs; go-live needs government/provider onboarding. |
| Captcha / login portals | **Never bypassed.** The checklist hands over to the human. |
| Portal submission | **Does not exist.** No code path submits to a government portal (enforced by a test). |

## Repository layout

```
backend/    FastAPI app (app/), Alembic (migrations/), tests, evals (evals/)
frontend/   Next.js App Router + next-intl (en/bn/hi), Playwright e2e
infra/      Terraform skeleton (India region), see infra/README.md
docs/       ARCHITECTURE, COMPLIANCE, SECURITY, INTEGRATIONS, RUNBOOK, PILOT_PLAN, DEMO_SCRIPT, LOAD_TEST, ASSUMPTIONS
scripts/    placeholder-form generator, key rotation, load test
```

## Configuration

Everything is environment-driven; see [.env.example](.env.example). Secrets never live in the repo. Key settings:
`ANTHROPIC_API_KEY` + `ANTHROPIC_MODEL` (model name is read from env, never hard-coded), `FIELD_ENCRYPTION_KEY`
(`make keygen`), `DEMO_MODE`, `RETENTION_DAYS`, `DATA_REGION`. Production refuses to start with dev secrets.

## Documentation

[Deployment](docs/DEPLOYMENT.md) · [Architecture](docs/ARCHITECTURE.md) · [DPDP compliance](docs/COMPLIANCE.md) · [Security / OWASP](docs/SECURITY.md) ·
[Integrations & going live](docs/INTEGRATIONS.md) · [Runbook](docs/RUNBOOK.md) · [Pilot plan](docs/PILOT_PLAN.md) ·
[Demo script](docs/DEMO_SCRIPT.md) · [Load test](docs/LOAD_TEST.md) · [Assumptions](docs/ASSUMPTIONS.md)
