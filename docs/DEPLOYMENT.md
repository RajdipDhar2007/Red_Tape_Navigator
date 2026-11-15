# Production deployment

This page covers the single-server route first (section 1 to 4), then managed hosting on Vercel and Render (last section).

One server (or VM) with Docker, DNS records for two hostnames, ports 80/443 open. Hosting in an Indian region is
recommended for data residency (see [COMPLIANCE](COMPLIANCE.md)). For managed cloud, use the container images and the
Terraform skeleton in [infra/](../infra/README.md); the environment variables are identical.

## 1. Configure

```bash
cp .env.prod.example .env.prod      # never commit this file
python -c "import secrets; print(secrets.token_urlsafe(48))"   # -> SECRET_KEY
make keygen                                                       # -> FIELD_ENCRYPTION_KEY (back it up!)
```

Fill in `WEB_DOMAIN`, `API_DOMAIN`, `POSTGRES_PASSWORD`, `GRIEVANCE_CONTACT` and the `SMTP_*` block (any provider: SES,
SendGrid, NIC mail; used for password-reset and reminder email). Set `GEMINI_API_KEY` + `GEMINI_MODEL` (the AI: intake gap-filling and live rule
verification; without them the app runs on its rules-first path). Optional: `SENTRY_DSN`, `METRICS_TOKEN`.

## 2. Start

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

Caddy obtains TLS certificates automatically. The API applies migrations and loads the curated rules pack on start.
The API **refuses to boot** on an unsafe configuration (dev secret, SQLite, localhost/non-https CORS, demo mode, no
grievance contact) and lists every problem at once.

## 3. Create the first officer account

Self-registration only creates citizens. Create staff accounts on the server:

```bash
ADMIN_PASSWORD='a-long-unique-passphrase' docker compose --env-file .env.prod -f docker-compose.prod.yml \
  exec -e PYTHONPATH=/app -e ADMIN_PASSWORD api python /app/scripts/create_admin.py officer@dept.gov.in admin
```

Roles: `admin` (everything), `reviewer` (review queue, stats, audit), `csc_operator` (review queue, stats). The officer
console is at `https://<WEB_DOMAIN>/en/staff`. Admins can change roles afterwards via `POST /admin/users/{id}/role`.

## 4. Verify

- `https://<API_DOMAIN>/ready` returns `{"status":"ready","demo_mode":false,...}`
- `https://<API_DOMAIN>/docs` returns 404 (API docs are disabled in production)
- The login page shows no "demo" banner or demo buttons.

## Operations

Backups, key rotation, retention purge and incident response are in the [RUNBOOK](RUNBOOK.md). Back up the `pgdata`
volume **and** `FIELD_ENCRYPTION_KEY`; one without the other cannot restore sensitive answers.

## Before real citizens use it

The rules pack is curated seed data, the PDF templates are placeholders and DigiLocker / e-Sign / UMANG / messaging are
simulated until you complete provider onboarding. [ASSUMPTIONS](ASSUMPTIONS.md) and [INTEGRATIONS](INTEGRATIONS.md)
list exactly what must be replaced, and [PILOT_PLAN](PILOT_PLAN.md) describes a safe rollout.

## Managed hosting: Vercel (web) and Render (API)

The web app and the API are separate deployables, so each can go to the platform that suits it. Nothing below is live yet; these are the steps and
settings the code expects.

| Part | Platform | How |
|---|---|---|
| Web app (`frontend/`) | **Vercel** | Import the repository, set **Root Directory** to `frontend`, framework Next.js. Set `NEXT_PUBLIC_API_URL` to the public API address (it is baked in at build time). `NEXT_PUBLIC_SITE_URL` is detected from Vercel; keep `NEXT_PUBLIC_LEGAL_REVIEWED=false` until a lawyer has approved the legal pages. |
| API (`backend/`) | **Render** web service (Docker) | Dockerfile `backend/Dockerfile`, root directory `backend`, health check `/health` (readiness is `/ready`). The entrypoint runs `alembic upgrade head` and loads the rules pack on start. |
| Worker | **Render** background worker (same image) | Start command `arq app.jobs.worker.WorkerSettings`; set `RUN_MIGRATIONS=false` and `SEED_ON_START=false`. On a single small instance you can skip the worker and Redis and set `RUN_SCHEDULER=true` on the API instead (never on more than one instance). |
| Database | **Render** PostgreSQL | The first migration runs `CREATE EXTENSION IF NOT EXISTS vector`. Free databases expire after 30 days: use a paid tier for anything real. |
| Cache and queue | **Render** Key Value (Redis) | Set `REDIS_URL`. Needed for shared rate limits and the worker queue. |
| Document Vault | S3-compatible bucket | Set `STORAGE_BACKEND=s3` and the `STORAGE_*` values; local disk on Render is wiped on every deploy. |

Settings the API needs in production (the API refuses to start and lists every problem if one is wrong):
`APP_ENV=prod`, `SECRET_KEY`, `FIELD_ENCRYPTION_KEY`, `DATABASE_URL`, `REDIS_URL`, `CORS_ORIGINS` and `WEB_BASE_URL` (both the real `https://` web address),
`TRUST_PROXY=true` (Render terminates TLS in front of the API), `DEMO_MODE=false`, `GRIEVANCE_CONTACT`, the `SMTP_*` block, `GEMINI_API_KEY` and `GEMINI_MODEL`.
Optional: `DIGIO_*`, `MSG91_*`, `SENTRY_DSN`, `METRICS_TOKEN`, `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` (first officer on a host without a shell; delete after the first sign-in).

After the first deploy run `python scripts/verify_deploy.py <api-url> <web-url> --journey` from your machine. Render has no India region (Singapore is the nearest), so if
data must stay in India use the single-server route in an Indian data centre, or the Terraform skeleton in [infra/](../infra/README.md) (`ap-south-1` or `ap-south-2`).
