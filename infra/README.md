# Infrastructure (Terraform-ready skeleton)

Local development uses `docker-compose.yml` at the repo root. This directory is the starting point for a cloud
deployment in an **Indian region** (data residency: see `docs/COMPLIANCE.md`). It is a *skeleton*: it pins the
provider/region and documents the intended modules, but creates no billable resources yet.

```
infra/terraform/
  versions.tf     provider + terraform version pins
  variables.tf    region (default ap-south-1 Mumbai), environment, names
  main.tf         provider, shared tags, data_region guard
  outputs.tf
  modules/
    network/      VPC, private subnets, egress rules (allow only needed outbound)   [TODO]
    database/     PostgreSQL 16 + pgvector (RDS/Aurora, encrypted, PITR, in-region backups) [TODO]
    cache/        Redis (ElastiCache), in-transit + at-rest encryption               [TODO]
    secrets/      Secrets Manager entries: SECRET_KEY, FIELD_ENCRYPTION_KEY, ANTHROPIC_API_KEY, DB URL [TODO]
    app/          container service for api / worker / web behind an ALB with TLS    [TODO]
```

Rules for the real implementation:
1. Keep all data stores and backups in `ap-south-1` (Mumbai) or `ap-south-2` (Hyderabad); `main.tf` fails the plan if a
   different region is used while `data_region_guard = true`.
2. No secrets in `.tf` or tfvars committed to git; use the secret manager and inject at runtime.
3. Run migrations as a one-off release task (`RUN_MIGRATIONS=true`); app replicas use `RUN_MIGRATIONS=false`.
4. Egress from the API should be limited to the official-domain allowlist (`backend/config/sources.yaml`) and the LLM
   endpoint, as defence in depth for the in-code allowlist.
5. Turn on WAF rate limiting in front of the ALB; the in-process limiter is per replica.
