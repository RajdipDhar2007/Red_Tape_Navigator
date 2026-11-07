#!/bin/sh
# Runs migrations (+ idempotent seed in demo mode) then starts the given command.
# In production run migrations as a separate release job and set RUN_MIGRATIONS=false.
set -e
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  alembic upgrade head
fi
if [ "${DEMO_MODE:-true}" = "true" ] && [ "${SEED_ON_START:-true}" = "true" ]; then
  python -m app.kb.seed_loader
fi
exec "$@"
