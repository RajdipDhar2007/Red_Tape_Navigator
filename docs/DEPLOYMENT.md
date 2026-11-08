# Production deployment

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
SendGrid, NIC mail; used for password-reset and reminder email). Optional: `ANTHROPIC_API_KEY` +
`ANTHROPIC_MODEL` (live rule verification), `SENTRY_DSN`, `METRICS_TOKEN`.

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
