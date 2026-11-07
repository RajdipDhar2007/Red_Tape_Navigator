# Load test and baseline

Script: `scripts/loadtest/locustfile.py` (Locust). Each virtual citizen registers, gives consent, states the goal
("bakery in Kolkata"), runs research, then repeatedly answers interview questions, reads the checklist, and loads the
review payload (which fills three PDFs). Raw numbers: `scripts/loadtest/baseline_stats.csv`.

```bash
cd backend
RATE_LIMIT_PER_MINUTE=1000000 AUTH_RATE_LIMIT_PER_MINUTE=1000000 \
  DATABASE_URL=sqlite+aiosqlite:///./data/load.db uvicorn app.main:app --port 8010 &
python -m app.kb.seed_loader          # the container entrypoint does this at boot
locust -f ../scripts/loadtest/locustfile.py --host http://localhost:8010 --headless -u 20 -r 5 -t 60s --csv ../scripts/loadtest/baseline
```

## Baseline (development laptop, single uvicorn worker, SQLite, no LLM)

20 concurrent users, 60 s, 1,260 requests, **0 failures**, ~21 req/s.

| Endpoint | req | avg ms | p50 | p95 |
|---|---:|---:|---:|---:|
| GET /health | 137 | 2 | 2 | 4 |
| GET /sessions/{id}/checklist | 242 | 6 | 5 | 10 |
| GET /sessions/{id}/interview | 386 | 5 | 4 | 7 |
| POST /sessions/{id}/interview | 280 | 18 | 12 | ~40 |
| GET /sessions/{id}/review (fills 3 PDFs) | 135 | 23 | 22 | ~35 |
| POST /sessions (goal parse) | 20 | 65 | 33 | n/a |
| POST /sessions/{id}/research (seeded KB) | 20 | 65 | 65 | n/a |
| POST /auth/register (bcrypt) | 20 | 2,329 | 2,300 | n/a |
| **Aggregate** | 1,260 | **48** | 5 | ~130 |

Caveats: this is a laptop with SQLite and the deterministic fallback agent. Real numbers with PostgreSQL, a network
hop, and live LLM calls (seconds per call) will differ. Re-baseline in the pilot environment before setting SLOs.

## What the load test found and fixed

1. **bcrypt blocked the event loop.** Registration averaged 4.3 s and stalled other requests. Hashing and verification
   now run in worker threads (`asyncio.to_thread`). Registration is still CPU-bound by design (cost factor 12), but it
   no longer blocks other users. Under 20 *simultaneous* registrations it costs ~2.3 s on this machine; real traffic is
   spread out. Auth endpoints are also rate-limited (20/min/IP) which bounds the CPU an attacker can burn.
2. **Cold-start seeding race.** Parallel first requests on an empty knowledge base each seeded the KB, creating duplicate
   "current" claims (`MultipleResultsFound`). Fixed with a partial unique index (`uq_claims_current_key`), graceful
   handling of the insert race in `upsert_claim`, and a lock around cold-start seeding. Regression tests added.
   Research latency fell from 766 ms to 65 ms average as a side effect.

## Suggested SLOs for a pilot (to be validated)

- p95 < 500 ms for non-LLM endpoints at 50 concurrent users per API replica.
- Research with live verification is asynchronous from the user's view: show progress, never block the UI > 30 s.
- Error rate < 0.5 %; zero uncited claims (enforced by the eval gate).
