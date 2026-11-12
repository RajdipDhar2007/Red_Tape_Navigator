# Put it online today, for free (about 30 minutes)

This is the shortest path to a public HTTPS site. It costs nothing and needs no card. Read the limits in step 0 first.
For a real launch (paid, with backups and a separate worker) use `render.production.yaml` and `docs/DEPLOYMENT_VERCEL_RENDER.md`.

Only the owner can do the sign-ups below: they create accounts and accept each provider's terms. Everything else is already in the repo.

## 0. What the free tier gives you, and what it does not

| | Free trial (`render.yaml`) | Launch (`render.production.yaml`) |
|---|---|---|
| Cost | US$0 | about US$30 a month (see `docs/FINAL_REPORT.md`) |
| API | sleeps after 15 idle minutes, about 1 minute to wake | always on |
| Database | **deleted 30 days after creation unless upgraded**, no backups | backups, no expiry |
| Reminders and clean-up jobs | run inside the API while it is awake | separate worker |
| Region | Singapore (Render has no India region) | Singapore |

Good for a demo, a pilot rehearsal and judging. Not for real citizens' data beyond a short trial.

## 1. An email sender (5 minutes)

The app refuses to start in production without one (password reset, email confirmation, reminders).

1. Create a free account at <https://www.brevo.com> (300 emails a day on the free plan; confirm the limit on their pricing page).
2. Senders, Domains: add and verify the address you will send from (for a trial your own Gmail address works; for launch verify a domain with SPF and DKIM).
3. SMTP and API, SMTP tab: note the **server** (`smtp-relay.brevo.com`), the **login** and generate an **SMTP key**. Keep the tab open.

Any SMTP provider works. On Render's free plan ports 25, 465 and 587 are blocked, so the provider must accept **port 2525** (Brevo, SendGrid and Mailgun do).

## 2. The backend on Render (10 minutes)

1. Sign up at <https://render.com> with "GitHub" and allow access to the `Red_Tape_Navigator` repository.
2. Open <https://render.com/deploy?repo=https://github.com/RajdipDhar2007/Red_Tape_Navigator> (or New, Blueprint, pick the repo). It reads `render.yaml`.
3. Render asks for these values. Type them there, never in chat:

| Variable | What to type |
|---|---|
| `CORS_ORIGINS` | `https://placeholder.example` for now (fixed in step 4) |
| `WEB_BASE_URL` | `https://placeholder.example` for now |
| `GRIEVANCE_CONTACT` | the email citizens can write to about their data |
| `SMTP_HOST` | `smtp-relay.brevo.com` |
| `SMTP_USERNAME` | the Brevo SMTP login |
| `SMTP_PASSWORD` | the Brevo SMTP key |
| `SMTP_FROM` | the sender address you verified |
| `BOOTSTRAP_ADMIN_EMAIL` | your email: this becomes the first officer account |
| `BOOTSTRAP_ADMIN_PASSWORD` | a new password of 12 or more characters |

4. Click Apply. The first build takes 5 to 10 minutes. When `rtn-api` is Live, open `https://<rtn-api>.onrender.com/ready`: it must say `"status":"ready"`, `"demo_mode":false` and a `kb_claims` number above zero.
5. In `rtn-api`, Environment, copy `FIELD_ENCRYPTION_KEY` into a password manager **now**. Losing it makes stored Aadhaar and PAN answers unreadable for ever.

## 3. The website on Vercel (5 minutes)

1. Sign up at <https://vercel.com> with "Continue with GitHub".
2. Add New, Project, import `Red_Tape_Navigator`.
3. Set **Root Directory** to `frontend`. Framework is detected as Next.js.
4. Environment Variables: `NEXT_PUBLIC_API_URL` = `https://<rtn-api>.onrender.com` (no trailing slash).
5. Deploy. Note the address Vercel gives you, for example `https://red-tape-navigator.vercel.app`.

Vercel's free Hobby plan is for non-commercial use. This product charges no one; check Vercel's terms against how you run it.

## 4. Connect the two (2 minutes)

In Render, `rtn-api`, Environment: set `CORS_ORIGINS` and `WEB_BASE_URL` to the exact Vercel address (https, no trailing slash). Save: the service restarts.

## 5. Check it (2 minutes)

```bash
cd backend && . .venv/Scripts/activate      # or .venv/bin/activate
python ../scripts/verify_deploy.py https://<rtn-api>.onrender.com https://<your-site>.vercel.app --journey
```

Every line must say `ok`. `--journey` signs up a throwaway account, builds a plan, and erases the account again.
Then by hand: open the site, create your own account, ask for a password reset and confirm the email arrives.

## 6. First officer and clean-up (2 minutes)

1. Sign in on the site with `BOOTSTRAP_ADMIN_EMAIL` and its password, open `/en/staff`: the officer console must load.
2. Your account, Change password. Turn on two-factor sign-in.
3. Back in Render, **delete** `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD`. (They can never overwrite an existing account's password, but there is no reason to keep them.)

## 7. Keep it awake and watched (3 minutes)

Create a free monitor at <https://uptimerobot.com> (or Better Stack): HTTPS, `https://<rtn-api>.onrender.com/ready`, every 5 minutes, alert to your email.
This also stops the free instance from sleeping, so reminders go out on time. One free instance awake all month fits inside Render's 750 free hours.

## 8. Before day 30

The free database is deleted 30 days after it was created. Either upgrade it in Render (Database, Change plan, `0.1c-256mb`, US$6 a month plus storage) or move to `render.production.yaml`. Put the date in your calendar today.

## If something fails

| Symptom | Cause and fix |
|---|---|
| Deploy log: `Unsafe production configuration: ...` | The message lists every missing or wrong variable. Fix them in Environment and save. |
| `/ready` says `kb_claims: 0` | The rules did not load: check the deploy log for the seed step, then Manual Deploy, Clear build cache and deploy. |
| Site loads, sign-up says "Could not sign in" | `CORS_ORIGINS` does not match the site address exactly, or `NEXT_PUBLIC_API_URL` is wrong (it is baked in at build: redeploy on Vercel after changing it). Run `verify_deploy.py`; it names the one that is wrong. |
| First request takes a minute | The free instance was asleep. Add the monitor in step 7. |
| No email arrives | `SMTP_PORT` must be `2525` on the free plan; the sender must be verified in Brevo; check the spam folder. |
