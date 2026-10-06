#!/usr/bin/env bash
# Restore the database from a dump stored in the `backups` volume.
#
#   ./scripts/restore.sh                      # latest dump, asks for confirmation
#   ./scripts/restore.sh app_20260101T000000Z.dump
#   ./scripts/restore.sh -y                   # no confirmation (for automation)
#
# The app is stopped during the restore so that nothing writes to the database.
set -euo pipefail

COMPOSE="${COMPOSE:-docker compose -p devops-template}"
ASSUME_YES=0
FILE=""

for arg in "$@"; do
    case "$arg" in
        -y|--yes) ASSUME_YES=1 ;;
        -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
        *) FILE="$arg" ;;
    esac
done

if [[ -z "$FILE" ]]; then
    FILE="$($COMPOSE exec -T backup sh -c 'ls -1t /backups/*.dump 2>/dev/null | head -n1')"
    [[ -n "$FILE" ]] || { echo "No dumps found in the backups volume" >&2; exit 1; }
else
    FILE="/backups/$(basename "$FILE")"
fi

$COMPOSE exec -T backup test -f "$FILE" || { echo "Dump not found: $FILE" >&2; exit 1; }

echo "Restoring database from: $FILE"
if [[ "$ASSUME_YES" != 1 ]]; then
    read -r -p "Current data will be REPLACED. Continue? [y/N] " answer
    [[ "$answer" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 1; }
fi

echo "Stopping app..."
$COMPOSE stop app

restore_rc=0
# --clean --if-exists drops existing objects before recreating them; one transaction = all or nothing.
$COMPOSE exec -T backup sh -c \
    'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --single-transaction "$1"' \
    _ "$FILE" || restore_rc=$?

echo "Starting app..."
$COMPOSE start app

if [[ "$restore_rc" != 0 ]]; then
    echo "pg_restore failed (exit $restore_rc); database left unchanged." >&2
    exit "$restore_rc"
fi
echo "Restore complete."
