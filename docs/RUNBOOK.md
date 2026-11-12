# Runbook

## Services and health
| Endpoint | Meaning |
|---|---|
| `GET /health` | liveness (process up) |
| `GET /ready` | readiness: DB reachable; reports `kb_claims`, `demo_mode`, `data_region` (503 when the DB is down) |
| `GET /metrics` | Prometheus (set `METRICS_TOKEN` to require `Authorization: Bearer …`; otherwise restrict at the network) |

Key metrics: `rtn_http_requests_total{route,status}`, `rtn_http_request_seconds`, `rtn_llm_calls_total{outcome}`,
`rtn_scrapes_total{outcome}`, `rtn_rate_limited_total`, `rtn_low_confidence_claims_total`.

Suggested alerts: 5xx rate > 1 % for 5 min; `rtn_llm_calls_total{outcome="error"}` > 20 % for 10 min;
`rtn_scrapes_total` failures > 50 % for 30 min; `/ready` failing; a burst of `rtn_rate_limited_total` on `/auth`.

Logs are JSON on stdout with `request_id` (also returned as `X-Request-ID`). They never contain request bodies, query
strings, or Aadhaar/PAN (redacted). Traces: set `OTEL_EXPORTER_OTLP_ENDPOINT`. Errors: set `SENTRY_DSN` (+ `pip install sentry-sdk`).

## Degraded modes (graceful degradation)
| Symptom | What happens | What users see | Action |
|---|---|---|---|
| No `ANTHROPIC_API_KEY`/model, or LLM circuit open | Rules-based intake/research on the seed KB | Checklist labelled "knowledge base (not live-verified)" | Check key/quota/provider status; the breaker half-opens after 45 s |
| Official sites down / blocked | Live verification skipped; KB served | "Official sites unreachable: showing saved knowledge base" | Check `rtn_scrapes_total`; per-host breaker resets after 60 s |
| Captcha/login wall | `HumanHandoffRequired` | Manual step in the checklist | None (by design) |
| Source page changed | Claims flagged `needs_verification`, review items created | "Verify with the authority" badge | Reviewer resolves in `/admin/review-queue` |
| Redis unavailable | Cache falls back to DB reads (Redis-backed cache only) | none | Restore Redis; workers need it for scheduled jobs |

## Human escalation (review queue)
Low-confidence claims (`< CONFIDENCE_THRESHOLD`, default 0.6), changed sources, and unknown municipalities create
`review_queue` rows. Roles `csc_operator`, `reviewer`, `admin` can `GET /admin/review-queue` and
`POST /admin/review-queue/{id}/resolve {status: verified|corrected|rejected, resolution}`. `verified` raises the claim's
confidence and clears the flag. SLA suggestion for the pilot: same business day.

## Deploy
1. CI green on `main`. 2. Run the **Deploy (template)** workflow (manual, requires environment approval).
3. Run migrations as a release job: `RUN_MIGRATIONS=true alembic upgrade head` (set `RUN_MIGRATIONS=false` on app
replicas). 4. Roll out api + worker + web. 5. Check `/ready` and the eval gate (`python -m evals.run`).
Rollback: redeploy the previous image tag; for schema, `alembic downgrade -1` only if the migration is reversible
(0001 is). Take a backup first.

Secrets (`SECRET_KEY`, `FIELD_ENCRYPTION_KEY`, `DATABASE_URL`, `ANTHROPIC_API_KEY`, `METRICS_TOKEN`) come from the
cloud secret manager. `APP_ENV=prod` refuses to start (listing every problem at once) if: `SECRET_KEY` is a dev/short value (<32 chars),
`FIELD_ENCRYPTION_KEY` is missing, `DATABASE_URL` is SQLite, `CORS_ORIGINS` is empty/localhost/non-https, or
`DEMO_MODE` is true.

## Backup and restore (PostgreSQL)
```bash
# nightly, in-region storage, encrypted at rest
pg_dump --format=custom --no-owner "$DATABASE_URL_SYNC" > rtn-$(date +%F).dump
# restore into a scratch database and verify
createdb rtn_restore && pg_restore --no-owner -d rtn_restore rtn-2026-01-01.dump
psql rtn_restore -c "select count(*) from claims; select count(*) from audit_log;"
```
* On the Docker Compose stack run the whole drill with one command: `sh scripts/backup_restore_drill.sh` (CI runs it on every push).
* Test a restore at least monthly. The audit chain must still verify after restore: `GET /admin/audit/verify`.
* Backups contain encrypted sensitive fields; keep the encryption key **separately** from the backup, and keep old keys
  until backups encrypted with them have expired.
* Retention interplay: purged sessions reappear if you restore an old dump. After any restore run `POST /admin/purge`
  and re-apply pending erasure requests (`privacy.erasure` audit entries list user ids).

## Key rotation
* `FIELD_ENCRYPTION_KEY`: `make keygen`; set `FIELD_ENCRYPTION_KEY="<new>,<old>"`; deploy; run
  `python scripts/rotate_encryption_key.py`; later drop `<old>` and redeploy.
* `SECRET_KEY`: changing it invalidates all sessions (users log in again).

## Routine jobs (Arq worker, or inside the API)
With `RUN_SCHEDULER=true` (the free-trial Blueprint) the same four jobs run inside the single API instance and no worker or Redis is needed.
Each run writes an audit entry `job.<name>` with `ok: true/false`; the last entry decides when the job is next due, so restarts do not repeat work.
Never set `RUN_SCHEDULER=true` on more than one instance.
On a brand-new deployment the two weekly jobs wait one week before their first run (audit detail `deferred: true`); an admin can run them
at once with `POST /admin/refresh` and `POST /admin/forms/refresh`.

Weekly `refresh_rules` (re-fetch sources, flag changes), daily `purge_job` (retention), half-hourly `reminders_job`.
Check the worker is running; each job logs its result.

## Data subject requests
Export: user calls `GET /privacy/export`. Erasure: `DELETE /privacy/me`. For assisted requests an admin identifies the
user id and confirms identity out-of-band before acting.

## Incident response (security / data breach)
1. Contain: revoke tokens (rotate `SECRET_KEY`), disable affected accounts, block IPs at the edge.
2. Assess: use the audit log (hash-chained; verify first) and request ids to scope who/what was accessed.
3. Notify: involve the DPO/legal immediately; notification to the Data Protection Board and affected data principals
   follows the Act and its rules (check current timelines).
4. Recover: rotate keys (see above), patch, restore if needed; write a post-incident review.

## Troubleshooting
* **429s from `/auth`:** expected under brute force; tune `AUTH_RATE_LIMIT_PER_MINUTE` (behind a proxy also set `TRUST_PROXY=true`).
* **Checklist empty:** goal missing city/state (clarifying question pending) or unknown activity: `409 goal_incomplete`.
* **PDF fields blank:** inspect the field report (`/sessions/{id}/review`): `missing`, `doubtful` (e.g. non-English text) or
  `unmapped` statuses explain each blank. Values are never guessed.
* **`MultipleResultsFound` on claims:** should be impossible (partial unique index `uq_claims_current_key`); if seen, run
  `alembic upgrade head` to ensure the index exists.
