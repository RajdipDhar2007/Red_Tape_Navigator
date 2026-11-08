#!/bin/sh
# Runs migrations, loads the (idempotent) curated rules pack, then starts the given command.
# SEED_ON_START defaults to "true": the rules KB must exist in production too, otherwise every plan is empty.
# Set RUN_MIGRATIONS=false on replicas when migrations run as a separate release step.
set -e
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  alembic upgrade head
fi
if [ "${SEED_ON_START:-true}" = "true" ]; then
  python -m app.kb.seed_loader
fi
exec "$@"
