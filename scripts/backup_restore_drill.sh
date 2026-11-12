#!/bin/sh
# Backup-and-restore drill for the Docker Compose stack: dumps the live database, restores it into a scratch database,
# and proves the copy holds the same rows. Nothing in the live database is changed. CI runs this on every push.
#
#   sh scripts/backup_restore_drill.sh                                               # dev stack (docker-compose.yml)
#   sh scripts/backup_restore_drill.sh --env-file .env.prod -f docker-compose.prod.yml   # production VM
#   KEEP_DUMP=1 sh scripts/backup_restore_drill.sh ...                               # keep the dump file as tonight's backup
#
# On a managed database (Render, Neon) use the same three commands with its connection string instead:
#   pg_dump --format=custom --no-owner "$URL" > rtn.dump ; createdb ... ; pg_restore --no-owner -d ... rtn.dump
set -eu

DB_USER="${DB_USER:-rtn}"
DB_NAME="${DB_NAME:-rtn}"
SCRATCH="${DB_NAME}_restore_drill"
DUMP="${DUMP:-rtn-$(date +%F-%H%M%S).dump}"
TABLES="users nav_sessions answers consents reminders claims audit_log"

dc() { docker compose "$@"; }
count() { dc "$@" exec -T db psql -U "$DB_USER" -d "$DB" -At -c "select count(*) from $TABLE"; }

echo "1/4 dump $DB_NAME -> $DUMP"
dc "$@" exec -T db pg_dump -U "$DB_USER" --format=custom --no-owner "$DB_NAME" > "$DUMP"
test -s "$DUMP" || { echo "DRILL FAIL: the dump is empty"; exit 1; }

echo "2/4 restore into scratch database $SCRATCH"
dc "$@" exec -T db dropdb -U "$DB_USER" --if-exists "$SCRATCH"
dc "$@" exec -T db createdb -U "$DB_USER" "$SCRATCH"
dc "$@" exec -T db pg_restore -U "$DB_USER" --no-owner --exit-on-error -d "$SCRATCH" < "$DUMP"

echo "3/4 compare row counts"
fail=0
for TABLE in $TABLES; do
  DB="$DB_NAME"; live=$(count "$@")
  DB="$SCRATCH"; copy=$(count "$@")
  if [ "$live" = "$copy" ]; then echo "  ok   $TABLE: $live rows"; else echo "  FAIL $TABLE: live=$live restored=$copy"; fail=1; fi
done
DB="$SCRATCH"; TABLE="claims"
[ "$(count "$@")" -gt 0 ] || { echo "  FAIL the restored copy has no rules"; fail=1; }

echo "4/4 clean up"
dc "$@" exec -T db dropdb -U "$DB_USER" "$SCRATCH"
[ "${KEEP_DUMP:-0}" = "1" ] && echo "kept $DUMP (store it encrypted, away from the encryption key)" || rm -f "$DUMP"

[ "$fail" = "0" ] && echo "DRILL PASSED: the backup restores and matches the live database." || { echo "DRILL FAILED"; exit 1; }
