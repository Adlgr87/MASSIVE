#!/bin/bash
# MASSIVE Factbook Database Backup
# Usage: ./scripts/backup_factbook.sh [backup_dir]
set -euo pipefail

BACKUP_DIR="${1:-/tmp/massive_backups/db}"
DATE=$(date +%Y%m%d_%H%M)
SNAPSHOT="factbook_${DATE}.sql"

mkdir -p "$BACKUP_DIR"

# SQLite dump (if database exists)
DB_PATH="${MASSIVE_DB_PATH:-massive.sqlite}"
if [ -f "$DB_PATH" ]; then
    sqlite3 "$DB_PATH" ".dump" > "$BACKUP_DIR/$SNAPSHOT"
    echo "✅ Factbook backup: $BACKUP_DIR/$SNAPSHOT"
    # Prune old backups (>24h)
    find "$BACKUP_DIR" -name "*.sql" -mtime +1 -delete
else
    echo "⚠️  No database found at $DB_PATH — skipping"
fi
