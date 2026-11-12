# Task list (commit + push after each)

- [x] 0. Repo created, monorepo skeleton
- [x] 1. Plan docs (ARCHITECTURE, ASSUMPTIONS, TASKS) + scaffold (pyproject, Makefile, .env.example, compose)
- [x] 2. Backend core: config, DB models, auth (JWT rotation, RBAC), consent, audit log (hash-chained)
- [x] 3. Scraping guard (allowlist, robots, sanitizer) + research agent + rules KB, citations, confidence, diff
- [x] 4. Interview engine + validators + encrypted memory
- [x] 5. Form registry (3 templates) + PDF filler + field report
- [x] 6. API routers, review checkpoint, follow-up, integrations adapters, e2e backend demo flow
- [x] 7. Frontend (Next.js, i18n en/bn/hi, voice, review UI)
- [x] 8. Hardening: headers, rate limit, metrics, tracing; evals (20 golden); coverage >= 80%
- [x] 9. Docker, CI/CD, load test, Playwright E2E
- [x] 10. Docs (COMPLIANCE, INTEGRATIONS, RUNBOOK, PILOT_PLAN, DEMO_SCRIPT) + final pass
- [x] 11. Accounts and teams, two-factor sign-in, full Hindi and Bengali, rules from official sources (see README section 4)
- [x] 12. Deployment readiness (2026-11-12): Render Blueprints, in-process scheduler, first officer from env, calendar export, help page,
       robots/sitemap/manifest, deploy checker, backup drill in CI, threat model, final report

## Pending
This file is the history of finished build steps. What is still to do lives in:
- `docs/OWNER_ACTIONS.md`: the owner's steps, in order, with a status for each (deployment is at part A, step 4).
- `docs/LAUNCH_CHECKLIST.md`: every go-live item; section 7a is the development backlog.
- `docs/FINAL_REPORT.md` section 4: the same items with who must do each.
