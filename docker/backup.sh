#!/bin/sh
# Periodic PostgreSQL backups with retention.
#   backup.sh         - loop forever: dump every BACKUP_INTERVAL_SECONDS
#   backup.sh once    - make a single dump and exit (used by `make backup`)
set -eu

BACKUP_DIR="${BACKUP_DIR:-/backups}"
INTERVAL="${BACKUP_INTERVAL_SECONDS:-21600}"   # 6 hours
KEEP="${BACKUP_KEEP:-7}"
: "${PGHOST:=db}"
export PGHOST

log() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) backup: $*"; }

dump() {
    ts="$(date -u +%Y%m%dT%H%M%SZ)"
    file="${BACKUP_DIR}/${POSTGRES_DB}_${ts}.dump"
    # Custom format (-Fc): compressed, restorable with pg_restore, supports --clean.
    if pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f "${file}.partial"; then
        mv "${file}.partial" "$file"
        log "created $file ($(du -h "$file" | cut -f1))"
    else
        rm -f "${file}.partial"
        log "ERROR: pg_dump failed"
        return 1
    fi
    # Retention: keep the newest $KEEP dumps.
    ls -1t "$BACKUP_DIR"/*.dump 2>/dev/null | tail -n "+$((KEEP + 1))" | while read -r old; do
        rm -f "$old" && log "removed old dump $old"
    done
}

mkdir -p "$BACKUP_DIR"

if [ "${1:-}" = "once" ]; then
    dump
    exit $?
fi

trap 'log "stopping"; exit 0' TERM INT
log "started: every ${INTERVAL}s, keep ${KEEP} dumps in ${BACKUP_DIR}"
while true; do
    dump || true
    sleep "$INTERVAL" &
    wait $!
done
