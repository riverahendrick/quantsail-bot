#!/usr/bin/env bash
# ── Quantsail PostgreSQL Backup Script ─────────────────────
# Run via cron: 0 */6 * * * /path/to/backup.sh
#
# Retains 7 days of backups with automatic rotation.
# Backups are compressed with gzip.

set -euo pipefail

# ── Configuration (override via environment) ───────────────
BACKUP_DIR="${BACKUP_DIR:-/var/backups/quantsail}"
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-quantsail}"
POSTGRES_DB="${POSTGRES_DB:-quantsail}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

# ── Setup ──────────────────────────────────────────────────
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/${POSTGRES_DB}_${TIMESTAMP}.sql.gz"
LOG_FILE="${BACKUP_DIR}/backup.log"

log() {
    echo "[$(date --iso-8601=seconds)] $*" | tee -a "$LOG_FILE"
}

# ── Backup ─────────────────────────────────────────────────
log "Starting backup: ${POSTGRES_DB}@${POSTGRES_HOST}:${POSTGRES_PORT}"

if pg_dump \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    --format=custom \
    --compress=6 \
    --no-owner \
    --no-acl \
    | gzip > "$BACKUP_FILE"; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log "Backup complete: $BACKUP_FILE ($SIZE)"
else
    log "ERROR: Backup failed!"
    rm -f "$BACKUP_FILE"
    exit 1
fi

# ── Rotation ───────────────────────────────────────────────
DELETED=$(find "$BACKUP_DIR" -name "${POSTGRES_DB}_*.sql.gz" -mtime +${RETENTION_DAYS} -print -delete | wc -l)
if [ "$DELETED" -gt 0 ]; then
    log "Rotated $DELETED old backup(s) (older than ${RETENTION_DAYS} days)"
fi

TOTAL=$(find "$BACKUP_DIR" -name "${POSTGRES_DB}_*.sql.gz" | wc -l)
log "Current backups on disk: $TOTAL"
