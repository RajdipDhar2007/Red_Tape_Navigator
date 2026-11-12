# Production Operations & Disaster-Recovery Runbook

## 1. Health, Liveness, Readiness & Metrics Endpoints

| Endpoint | Auth | Purpose & HTTP Behavior |
| :--- | :--- | :--- |
| `GET /health`<br>`GET /health/live` | Public | **Liveness:** Confirms the FastAPI process is running (`200 OK`, `{"status": "ok", "live": true, "disclaimer": "..."}`). Never queries external dependencies. |
| `GET /ready`<br>`GET /health/ready` | Public | **Readiness:** Confirms PostgreSQL/SQLite is reachable (`SELECT 1`) and the rules knowledge base (`Claim` count) is loaded (`200 OK`), plus non-secret Redis status (`ok`, `degraded`, `unconfigured`), `storage_backend`, and `storage_warning` if `STORAGE_BACKEND=local` is used in `APP_ENV=prod`. Returns `503 Service Unavailable` (`{"status": "unavailable", "ready": false, "database": false}`) if the database is unreachable. |
| `GET /admin/readiness` | Staff (`csc_operator`, `reviewer`, `admin`) | **Operational & Provider Readiness Matrix:** Reports detailed configuration and reachability of `database`, `redis`, `storage` (including `durable` and `production_warning`), and external providers (`llm`, `smtp`, `msg91`, `digio`, `sentry`, `otel`, `whatsapp`, `umang`) without exposing secrets or making billable third-party calls. |
| `GET /metrics` | Optional `Bearer <METRICS_TOKEN>` | **Prometheus Metrics:** Exposes `rtn_http_requests_total{route,status}`, `rtn_http_request_seconds`, `rtn_llm_calls_total{outcome}`, `rtn_scrapes_total{outcome}`, `rtn_rate_limited_total`, and `rtn_low_confidence_claims_total`. |

### Suggested Alerts
- **Critical (Page Immediately):**
  - `/health/ready` returning `503` for > 2 minutes.
  - 5xx error rate > 1% over 5 minutes.
  - Audit chain verification (`GET /admin/audit/verify`) returning `chain_valid: false`.
- **Warning (Ticket / Next Business Hour):**
  - `/health/ready` reporting `redis: "degraded"` or `storage_warning` non-null in production.
  - `rtn_llm_calls_total{outcome="error"}` > 20% over 10 minutes.
  - `rtn_scrapes_total{outcome="error"}` > 50% over 30 minutes.
  - Sustained burst of `rtn_rate_limited_total` on `/auth/*`.

---

## 2. Structured Logging, Redaction & Error Observability

- **Format:** Structured JSON logs on `stdout` via `structlog` (`backend/app/core/logging.py`), including UTC ISO-8601 `timestamp`, `level`, `event`, and `request_id` (matching the `X-Request-ID` response header).
- **Automatic Redaction (`backend/app/core/crypto.py`):**
  - Every log event and exception context passes through `redact()`, which recursively masks:
    - Sensitive dictionary keys: `aadhaar`, `pan`, `aadhaar_number`, `pan_number`, `bank_account_number`, `bank_ifsc`, `ifsc`, `totp_secret`, `password`, `new_password`, `current_password`, `smtp_password`, `postgres_password`, `secret`, `secret_key`, `field_encryption_key`, `api_key`, `anthropic_api_key`, `msg91_authkey`, `digio_client_secret`, `digio_webhook_secret`, `storage_secret_access_key`, `metrics_token`, `sentry_dsn`, `token`, `access_token`, `refresh_token`, `reset_token`, `authorization`, `cookie`, `otp`, `recovery_code`, `recovery_hashes`, `content_bytes`, `file_bytes`, `raw_bytes`, `pdf`.
    - Sensitive string patterns: 12-digit Aadhaar patterns (`[AADHAAR-REDACTED]`), 10-character PAN patterns (`[PAN-REDACTED]`), JWT tokens (`[JWT-REDACTED]`), and PostgreSQL connection string passwords (`postgresql://user:[REDACTED]@host/db`).
    - Raw `bytes`/`bytearray` payloads (`[BINARY-REDACTED]`).
- **Unhandled Exceptions & Sentry (`backend/app/core/errors.py`):**
  - Unhandled exceptions return a generic `500 {"detail": "Internal error"}` response (never leaking stack traces) and log `unhandled_exception` with `error_type` and redacted context.
  - When `SENTRY_DSN` is set (and `sentry-sdk` is installed), Sentry is initialized with `send_default_pii=False` and `traces_sample_rate=0.0`. When `SENTRY_DSN` is unset, the application operates normally without external dependency.

---

## 3. Database Backup & Restore Readiness (`scripts/db_backup_restore.py`)

> **Important:** Do not claim automated backups are running until the hosting provider's backup schedule or cron job is provisioned by the infrastructure owner.

### Backup & Restore Targets (Recommendations — Require Owner Approval)
- **Recommended RPO (Recovery Point Objective):** ≤ 24 hours (daily automated snapshots + `pg_dump`) or ≤ 15 minutes if managed PostgreSQL Point-in-Time Recovery (PITR / WAL archiving) is enabled by the owner.
- **Recommended RTO (Recovery Time Objective):** ≤ 2 hours for full service restoration and verification.
- **Recommended Backup Frequency & Retention:**
  - Daily compressed `pg_dump` custom-format backups retained for **30 days** in encrypted, in-region object storage (`ap-south-1` / India region where required by compliance).
  - Weekly backups retained for **90 days** (aligned with `RETENTION_DAYS=90` DPDP session retention).
- **Restore Verification Cadence:** At least **monthly** into an isolated non-production verification database (`*_restore` or `*_verify`).

### Safe Backup Execution
Use `scripts/db_backup_restore.py` (which passes `PGPASSWORD` via subprocess environment and never prints credentials on the command line or in logs):

```bash
# 1. Dry-run to inspect the redacted pg_dump command:
python scripts/db_backup_restore.py backup --output-dir ./backups --dry-run

# 2. Run a live compressed backup (writes ./backups/rtn-backup-YYYYMMDDTHHMMSSZ.dump):
DATABASE_URL="postgresql://rtn:YOUR_PASSWORD@db-host:5432/rtn" \
  python scripts/db_backup_restore.py backup --output-dir ./backups
```

### Safe Non-Production Restore Verification Workflow
`scripts/db_backup_restore.py restore-verify` enforces strict guardrails:
1. Refuses to run when `APP_ENV=prod`.
2. Requires **both** the `--confirm-non-prod-restore` CLI flag **and** `CONFIRM_NON_PROD_RESTORE=YES_RESTORE_NON_PROD` in the environment.
3. Refuses to run if `--target-url` matches `DATABASE_URL` (the primary database).
4. Refuses to run if the target host or database name contains production tokens (`prod`, `production`, `primary`, `live`, `master`, `main`) or does not end with an explicit verification suffix (`_restore`, `_verify`, `_test`, `_scratch`, `_dr`).
5. Automatically runs post-restore SQL checks (`alembic_version`, `claims` count, `audit_log` count).

```bash
# Create an isolated scratch database first:
createdb rtn_restore

# Restore and verify schema/migrations against rtn_restore:
APP_ENV=dev \
CONFIRM_NON_PROD_RESTORE=YES_RESTORE_NON_PROD \
  python scripts/db_backup_restore.py restore-verify \
  --dump-file ./backups/rtn-backup-20261112T020000Z.dump \
  --target-url "postgresql://postgres:localpass@localhost:5432/rtn_restore" \
  --primary-url "$DATABASE_URL" \
  --confirm-non-prod-restore
```

### Post-Restore Privacy & Encryption Interplay
- **Encryption Keys:** Database backups contain Fernet-encrypted Aadhaar, PAN, bank, and TOTP secrets. Store `FIELD_ENCRYPTION_KEY` in a separate secret manager (never inside the database dump bucket), and retain previous rotation keys until all backups encrypted with them have expired.
- **DPDP Erasure & Retention Replay:** Restoring an older backup can reintroduce sessions that expired or users who exercised `DELETE /privacy/me` after the backup timestamp. Immediately after any production recovery:
  1. Verify audit chain integrity: `GET /admin/audit/verify`.
  2. Run retention purge: `POST /admin/purge`.
  3. Re-apply any `privacy.erasure` audit events recorded after the backup timestamp.

---

## 4. Document Vault Storage Durability Audit

| Storage Mode | Configuration | Durability & Operational Characteristics | Appropriate Use |
| :--- | :--- | :--- | :--- |
| **1. Local Ephemeral Disk** | `STORAGE_BACKEND=local` on stateless container platforms (e.g. Render default disk without a mounted volume) | **Ephemeral:** Container restarts or redeployments wipe `/app/data/vault`, leaving `Document` database rows pointing to missing files (`404 Document file is unavailable in storage`). `/health/ready` and `/admin/readiness` emit a `storage_warning` / `production_warning` when `STORAGE_BACKEND=local` in `APP_ENV=prod`. | Local development and automated tests only. |
| **2. Persistent Mounted Volume** | `STORAGE_BACKEND=local` with `vaultdata:/var/lib/rtn/vault` mounted on both `api` and `worker` (`docker-compose.prod.yml`) | **Single-Host Durable:** Survives container restarts and allows `worker` (`purge_job`) to delete expired files. Requires host-level disk snapshots (`rsync` / LVM / EBS snapshot) for off-host disaster recovery. | Single-node Docker Compose deployments with scheduled volume backups. |
| **3. S3-Compatible Object Storage** | `STORAGE_BACKEND=s3` with `STORAGE_BUCKET`, `STORAGE_REGION`, `STORAGE_ACCESS_KEY_ID`, `STORAGE_SECRET_ACCESS_KEY` (AWS S3 / Cloudflare R2 / MinIO) | **Multi-AZ Durable (Recommended for Production):** Decouples file durability from application containers; supports horizontal scaling across multiple API/worker replicas. | All multi-replica or cloud PaaS production deployments. |

### Object Storage Backup & Security Recommendations
1. **Enable Bucket Versioning:** Turn on S3/R2 object versioning so accidental overwrites can be recovered, paired with a lifecycle rule to permanently expire non-current object versions after **7–14 days** (respecting DPDP erasure obligations).
2. **Server-Side Encryption:** Enable SSE-S3 (`AES-256`) or SSE-KMS at the bucket level and block all public bucket ACLs (`BlockPublicAccess`).
3. **Least-Privilege IAM:** Restrict the application's `STORAGE_ACCESS_KEY_ID` to `s3:PutObject`, `s3:GetObject`, and `s3:DeleteObject` on `arn:aws:s3:::<bucket>/vault/*` only.

---

## 5. Redis, Cache & Background Worker Operations

| Component | Normal Behavior (`REDIS_URL` healthy) | Degraded Behavior (`REDIS_URL` unreachable / unset) | Operator Action |
| :--- | :--- | :--- | :--- |
| **Rate Limiter (`middleware.py`)** | Shared atomic `INCR` + `EXPIRE` sliding window across all API workers. | Logs `rate_limiter_redis_unavailable` (without IPs/PII) and falls back automatically to per-worker bounded in-memory sliding window (`max_keys=10,000`). | Check `/health/ready` (`redis: "degraded"`) and restore Redis. |
| **Cache (`cache.py`)** | `RedisCache` caches non-sensitive lookups with 1s socket timeout. | Logs `cache_unavailable` (`op`, `error_type`) and degrades to cache miss; PostgreSQL remains the source of truth. | Restore Redis; no citizen data is lost. |
| **Background Worker (`jobs/worker.py`)** | Arq runs scheduled cron jobs (`refresh_rules`, `forms_job`, `purge_job`, `reminders_job`), logging `worker_job_started` and `worker_job_completed`. | Worker jobs pause while Redis is unreachable; if a job raises an exception, `_run_observed` logs `unhandled_exception` with `job=<name>` and reports to Sentry. | Once Redis recovers, Arq resumes cron scheduling. Run `POST /admin/purge` or `POST /admin/refresh` manually from the Officer Console if needed. |
| **Reminders (`followup/reminders.py`)** | `dispatch_due` queries `Reminder.sent == False` with `due_at <= now`. Reminders remain `sent=False` in PostgreSQL until the provider returns `res.ok=True`. | Undispatched due reminders stay safely in PostgreSQL (`sent=False`) and are picked up on the next `reminders_job` run after recovery. | Check provider credentials in `/admin/readiness`. |

---

## 6. Incident Response & Disaster-Recovery Playbooks

### Incident 1: Database Outage (PostgreSQL Unreachable or Corrupted)
1. **Detection:** `/health/ready` returns `503 Service Unavailable` (`{"status": "unavailable", "ready": false, "database": false}`); API requests fail with `500`/`503`.
2. **Immediate Containment:** Put the edge proxy / status page in maintenance notice if downtime exceeds 5 minutes; pause the Arq worker (`docker compose stop worker` or scale `rtn-worker` to 0) to stop background retry noise.
3. **Safe Recovery Steps:**
   - Check managed DB health, disk full conditions, or connection pool exhaustion (`pg_stat_activity`).
   - If hardware/instance failure requires restoration from backup: provision a replacement PostgreSQL instance with `pgvector`, verify the dump in a `*_restore` DB first using `scripts/db_backup_restore.py restore-verify`, then restore to the new instance and run `alembic upgrade head`.
4. **Verification:** Confirm `GET /health/ready` returns `200 OK` (`kb_claims: 438`), run `GET /admin/audit/verify` (`chain_valid: true`), and execute `POST /admin/purge` to clean any expired sessions present in the backup.
5. **Escalation:** Database Administrator / Infrastructure Owner; notify Data Protection Officer (DPO) if data loss or corruption is suspected.

### Incident 2: Redis Outage
1. **Detection:** `/health/ready` returns `200 OK` with `"redis": "degraded"`; logs show `rate_limiter_redis_unavailable` or `cache_unavailable`; `arq --check` healthcheck on `worker` fails.
2. **Immediate Containment:** None required for the API—rate limiting and caching automatically fail over to in-memory/PostgreSQL so citizens can continue using the application.
3. **Safe Recovery Steps:** Restart or reprovision the Redis instance (`docker compose restart redis` or managed Redis failover). Redis holds only transient rate-limit counters, cache entries, and Arq job queues (all persistent state is in PostgreSQL).
4. **Verification:** Confirm `/health/ready` shows `"redis": "ok"`, `/admin/readiness` shows `redis.reachable: true`, and `worker` logs `worker_job_started` on its next half-hourly `reminders_job` tick.
5. **Escalation:** Platform / DevOps Engineer if Redis fails to restart within 15 minutes.

### Incident 3: Application Crash / Bad Deployment
1. **Detection:** `/health/live` fails or container restart loop (`CrashLoopBackOff`); startup fails fast with `RuntimeError: Unsafe production configuration: ...` if an invalid env var was deployed.
2. **Immediate Containment:** Keep previous healthy container revision serving traffic (Render / Docker rollback); do not force-bypass `production_problems()` checks.
3. **Safe Recovery Steps:**
   - Inspect container startup logs (`structlog` output). If caused by a missing/invalid env var, fix the environment configuration.
   - If caused by a code regression, roll back to the previous image tag. Only run `alembic downgrade -1` if the release included a reversible schema migration and a pre-deploy DB backup was taken.
4. **Verification:** Check `/health/live` (`200`), `/health/ready` (`200`), and run `python -m evals.run`.
5. **Escalation:** Release Engineer / On-Call Lead.

### Incident 4: Object Storage Outage (S3 / R2 or Volume Unreachable)
1. **Detection:** Document Vault uploads (`POST /documents`) or downloads (`GET /documents/{id}/download`) fail with `500`/`404`, while core intake, planner, interview, and PDF form generation continue working normally.
2. **Immediate Containment:** Core licence navigation and form filling do not depend on the Document Vault; keep the main application online.
3. **Safe Recovery Steps:**
   - Check S3/R2 provider status, IAM credentials (`STORAGE_ACCESS_KEY_ID` / `STORAGE_SECRET_ACCESS_KEY`), and endpoint reachability (`STORAGE_ENDPOINT_URL`).
   - For `docker-compose.prod.yml` local volume deployments, verify `/var/lib/rtn/vault` disk space (`df -h`) and ownership (`uid=10001`).
4. **Verification:** Check `/admin/readiness` (`storage.configured: true`) and test uploading/downloading a small test PDF in `/documents`.
5. **Escalation:** Cloud Infrastructure Owner.

### Incident 5: External Provider Outage (Anthropic, SMTP, MSG91, Digio)
1. **Detection:**
   - **Anthropic LLM:** `rtn_llm_calls_total{outcome="error"}` spikes; circuit breaker opens after 3 failures for 45 seconds.
   - **SMTP / MSG91 / Digio:** Structured warning logs (`smtp_send_failed`, `msg91_network_error`, `digio_http_error`) with status/error type (no PII).
2. **Immediate Containment:** Automatic—no manual intervention required to protect core uptime:
   - LLM outage automatically falls back to deterministic rules intake/planner (`agent_mode: "rules_fallback"`).
   - SMTP / MSG91 / Digio failures return clear structured `AdapterResult(ok=False)` errors without crashing sessions or marking unsent reminders as sent.
3. **Safe Recovery Steps:** Verify provider status page, check API key/quota/sender verification, and confirm configuration in `/admin/readiness`.
4. **Verification:** Circuit breaker auto-resets once provider responds; due reminders (`sent=False`) automatically dispatch on the next `reminders_job` cycle.
5. **Escalation:** Third-Party Vendor Support / Account Owner.

### Incident 6: Encryption Key Rotation or Compromise (`FIELD_ENCRYPTION_KEY` / `SECRET_KEY`)
1. **Detection:** Scheduled key rotation drill, or suspected credential exposure.
2. **Immediate Containment:**
   - If `SECRET_KEY` (JWT signing) is compromised: generate a new 48-byte random secret (`python -c "import secrets;print(secrets.token_urlsafe(48))"`), update `SECRET_KEY` on both `api` and `worker`, and redeploy (immediately invalidates all active tokens).
   - If `FIELD_ENCRYPTION_KEY` is being rotated: **never delete the old key before re-encrypting existing rows!**
3. **Safe Recovery Steps (`FIELD_ENCRYPTION_KEY` Rotation):**
   1. Take a full PostgreSQL backup first (`python scripts/db_backup_restore.py backup`).
   2. Generate a new Fernet key (`make keygen`).
   3. Set `FIELD_ENCRYPTION_KEY="<new_key>,<old_key>"` on both `api` and `worker` (`MultiFernet` encrypts new values with `<new_key>` and decrypts with either key).
   4. Run `python scripts/rotate_encryption_key.py` to re-encrypt all sensitive `Answer.value` rows and `User.totp_secret` values under `<new_key>`.
   5. After verifying login/2FA and answer decryption, remove `<old_key>` from active `FIELD_ENCRYPTION_KEY` (keep `<old_key>` archived in offline secret storage until all backups predating the rotation have expired).
4. **Verification:** Run `GET /admin/audit/verify` and test citizen 2FA login and `/privacy/export`.
5. **Escalation:** Security Lead & Data Protection Officer (DPO).
