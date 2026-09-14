#!/bin/bash
# MASSIVE Backup Verification
# Usage: ./scripts/verify_backup.sh
set -euo pipefail

BACKUP_DIR="${MASSIVE_BACKUP_DIR:-/tmp/massive_backups}"
OK=0
FAIL=0

echo "=== MASSIVE Backup Verification ==="

# Check factbook backups (last 24h)
DB_BACKUPS="$BACKUP_DIR/db"
if [ -d "$DB_BACKUPS" ] && ls "$DB_BACKUPS"/*.sql 1>/dev/null 2>&1; then
    LATEST=$(ls -t "$DB_BACKUPS"/*.sql | head -1)
    if [ -f "$LATEST" ] && [ $(stat -c %s "$LATEST" 2>/dev/null || stat -f %z "$LATEST") -gt 0 ]; then
        echo "✅ Factbook backup: $LATEST"
        OK=$((OK+1))
    else
        echo "❌ Empty or missing: $LATEST"
        FAIL=$((FAIL+1))
    fi
else
    echo "⚠️  No factbook backups found in $DB_BACKUPS"
fi

# Check model backups
MODEL_BACKUPS="$BACKUP_DIR/models"
if [ -d "$MODEL_BACKUPS" ]; then
    COUNT=$(find "$MODEL_BACKUPS" -name "*.pt" 2>/dev/null | wc -l)
    if [ "$COUNT" -gt 0 ]; then
        echo "✅ Model backups: $COUNT files found"
        OK=$((OK+1))
    else
        echo "⚠️  No model backups found"
    fi
else
    echo "⚠️  No model backup directory: $MODEL_BACKUPS"
fi

echo ""
echo "Result: $OK OK, $FAIL FAILED"
exit $FAIL
