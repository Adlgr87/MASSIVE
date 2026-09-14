#!/bin/bash
# MASSIVE Model Artifacts Backup
# Usage: ./scripts/backup_models.sh [source_dir] [backup_dir]
set -euo pipefail

MODEL_DIR="${1:-models/cfc_calibrated}"
BACKUP_DIR="${2:-/tmp/massive_backups/models}"
DATE=$(date +%Y%m%d_%H%M)

mkdir -p "$BACKUP_DIR/$DATE"

if [ -d "$MODEL_DIR" ]; then
    cp -r "$MODEL_DIR"/* "$BACKUP_DIR/$DATE/" 2>/dev/null || true
    echo "✅ Models backup: $BACKUP_DIR/$DATE/"
else
    echo "⚠️  Model directory not found: $MODEL_DIR"
fi
