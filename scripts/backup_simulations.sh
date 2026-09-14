#!/bin/bash
# MASSIVE Simulation History Backup
# Usage: ./scripts/backup_simulations.sh
set -euo pipefail

BACKUP_DIR="${MASSIVE_BACKUP_DIR:-/tmp/massive_backups/sims}"
DATE=$(date +%Y%m%d_%H%M)
SIM_DIR="massive.sqlite"

mkdir -p "$BACKUP_DIR"

# Backup the entire SQLite database as JSON snapshot
if [ -f "$SIM_DIR" ]; then
    sqlite3 "$SIM_DIR" ".schema" > "$BACKUP_DIR/${DATE}_schema.sql"
    sqlite3 "$SIM_DIR" "SELECT name FROM sqlite_master WHERE type='table';" | while read -r table; do
        sqlite3 "$SIM_DIR" ".mode json" "SELECT * FROM $table;" > "$BACKUP_DIR/${DATE}_${table}.json"
    done
    echo "✅ Simulations backup: $BACKUP_DIR/$DATE/"
else
    echo "⚠️  No simulation database found"
fi
