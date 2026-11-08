# Deploying: frontend on Vercel, backend on Render

```
Citizen browser --> Vercel (Next.js web) --https--> Render (rtn-api) --> Postgres + Redis
                                                      rtn-worker (reminders, form re-checks)
```

## 1. Backend on Render

1. In Render: **New > Blueprint**, connect this GitHub repo, pick `render.yaml`. It creates Postgres, Redis, `rtn-api` and `rtn-worker`.
2. Fill the `sync:false` values in `rtn-api` (use the same values on `rtn-worker`; an Environment Group is easiest):
   - `FIELD_ENCRYPTION_KEY`: generate with `make keygen`. **Back it up**; losing it makes stored Aadhaar/PAN answers unreadable.
   - `CORS_ORIGINS` and `WEB_BASE_URL`: `https://<your-vercel-domain>` (https only, no trailing slash).
   - `GRIEVANCE_CONTACT`, `SMTP_*`. The API refuses to start in prod without them (see `production_problems`).
3. The container entrypoint runs `alembic upgrade head` and loads the rules pack on start. Migration 0001 runs
   `CREATE EXTENSION vector`, which Render Postgres allows.
4. Create the first officer (Render shell on `rtn-api`):
   `ADMIN_PASSWORD='...' PYTHONPATH=/app python /scripts/create_admin.py officer@dept.gov.in admin`
   (copy `scripts/create_admin.py` into the image or run it from a one-off job).
5. Check `https://<rtn-api>.onrender.com/ready`.

## 2. Frontend on Vercel

1. **Add New Project**, import this repo, set **Root Directory** to `frontend`.
2. Environment variable (Production): `NEXT_PUBLIC_API_URL=https://<rtn-api>.onrender.com` (or your custom API domain).
   It is baked in at build time, so redeploy after changing it. The CSP in `next.config.mjs` derives from it.
3. Optional env vars (Production): `NEXT_PUBLIC_LEGAL_REVIEWED=true` hides the "draft, pending legal review" banner on
   `/privacy` and `/terms`. Set it ONLY after counsel has approved the text in `frontend/messages/*.json` (`legal` section).
   `NEXT_PUBLIC_EMBLEM_URL` lets an authorised department supply its own emblem.
4. Add your custom domain in Vercel, then use that exact origin in the backend's `CORS_ORIGINS` / `WEB_BASE_URL`.

## 3. Things to know

- **Region:** Render has no India region (closest: Singapore). The Blueprint sets `DATA_REGION=ap-singapore` so the privacy
  notice stays truthful. If the department requires in-India storage, use an Indian cloud for the backend instead.
- **Cross-site calls:** web and API are on different domains, so the browser calls the API directly (CORS + bearer tokens in
  sessionStorage, as designed). Put both under one parent domain if you later want cookie-based sessions.
- **Plans:** `starter` and `basic-256mb` are minimums for a pilot. Size up before launch (see `docs/LOAD_TEST.md`).
- `autoDeploy` is off on purpose: deploy deliberately after tests pass.
