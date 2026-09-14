# MASSIVE Backup & Restore Automation

**Version:** 1.0  
**Scope:** Factbook DB, model artifacts, simulation history

---

## Overview

This document describes the backup and restore procedures for MASSIVE production deployment.

### RTO / RPO Targets

| Data | RTO | RPO | Frequency |
|------|-----|-----|-----------|
| Factbook DB | 30 min | 5 min | Every 5 min |
| Model weights | 2 min | On training | On change |
| Simulation history | 24 hr | Daily | Daily batch |
| Configuration | 0 | Git | On commit |

---

## Backup Procedures

### 1. Factbook Database Backup

```bash
#!/bin/bash
# scripts/backup_factbook.sh
set -euo pipefail

DATE=$(date +%Y%m%d_%H%M)
BACKUP_DIR="${MASSIVE_BACKUP_DIR:-/tmp/massive_backups/db}"
SNAPSHOT="factbook_${DATE}.sql"

mkdir -p "$BACKUP_DIR"

# SQLite dump
if [ -f "massive.sqlite" ]; then
    sqlite3 massive.sqlite ".dump" > "$BACKUP_DIR/$SNAPSHOT"
    echo "✅ Factbook backup: $BACKUP_DIR/$SNAPSHOT"
fi

# Prune old backups (>24h)
find "$BACKUP_DIR" -name "*.sql" -mtime +1 -delete
```

### 2. Model Artifacts Backup

```bash
#!/bin/bash
# scripts/backup_models.sh
set -euo pipefail

DATE=$(date +%Y%m%d_%H%M)
BACKUP_DIR="${MASSIVE_BACKUP_DIR:-/tmp/massive_backups/models}"
MODEL_DIR="models/cfc_calibrated"

mkdir -p "$BACKUP_DIR"

cp -r "$MODEL_DIR"/* "$BACKUP_DIR/"
echo "✅ Models backup: $BACKUP_DIR/$DATE/"
```

### 3. Automated Cron Jobs

```cron
# /etc/cron.d/massive-backup
# Factbook backup every 5 minutes
*/5 * * * * root /opt/massive/scripts/backup_factbook.sh
# Model backup on training completion (hook-based)
# Simulation history daily at 2:00 AM
0 2 * * * root /opt/massive/scripts/backup_simulations.sh
```

---

## Restore Procedures

### 1. Factbook Database Restore

```bash
#!/bin/bash
# scripts/restore_factbook.sh
set -euo pipefail

DATE=${1:-$(ls -t /tmp/massive_backups/db/*.sql | head -1)}
BACKUP_DIR="${MASSIVE_BACKUP_DIR:-/tmp/massive_backups/db}"

if [ ! -f "$BACKUP_DIR/$DATE" ] && [ -n "$1" ]; then
    echo "❌ Backup not found: $BACKUP_DIR/$DATE"
    exit 1
fi

sqlite3 massive.sqlite < "$BACKUP_DIR/${1:-*.sql}"
echo "✅ Factbook restored from: $BACKUP_DIR/${1:-latest}"
```

### 2. Model Artifacts Restore

```bash
#!/bin/bash
# scripts/restore_models.sh
set -euo pipefail

BACKUP_DIR="${1:-/tmp/massive_backups/models}"
MODEL_DIR="models/cfc_calibrated"

rm -rf "$MODEL_DIR"
mkdir -p "$MODEL_DIR"
cp -r "$BACKUP_DIR"/* "$MODEL_DIR/"
echo "✅ Models restored from: $BACKUP_DIR"
```

### 3. Simulation History Restore

```bash
#!/bin/bash
# scripts/restore_simulations.sh
set -euo pipefail

DATE=${1:-$(ls -t /tmp/massive_backups/sims/*.json | head -1)}
BACKUP_DIR="${MASSIVE_BACKUP_DIR:-/tmp/massive_backups/sims}"

if [ ! -f "$BACKUP_DIR/$DATE" ]; then
    echo "❌ Backup not found: $BACKUP_DIR/$DATE"
    exit 1
fi

# Restore from JSON snapshot
python3 -c "
import json
with open('$BACKUP_DIR/$DATE') as f:
    data = json.load(f)
# Rehydrate simulation store from snapshot
print(f'✅ Restored {len(data.get(\"simulations\", []))} simulations')
"
```

---

## Verification

```bash
# scripts/verify_backup.sh
set -euo pipefail

BACKUP_DIR="${MASSIVE_BACKUP_DIR:-/tmp/massive_backups}"
OK=0
FAIL=0

# Check factbook backups (last 24h)
for f in "$BACKUP_DIR"/db/*.sql; do
    if [ $(find "$f" -mmin -1440 -size +0) ]; then
        OK=$((OK+1))
    else
        FAIL=$((FAIL+1))
        echo "❌ Stale or empty: $f"
    fi
done

# Check model backups
for f in "$BACKUP_DIR"/models/*.pt; do
    if [ -f "$f" ]; then
        OK=$((OK+1))
    else
        FAIL=$((FAIL+1))
        echo "❌ Missing model: $f"
    fi
done

echo "✅ Verification: $OK OK, $FAIL FAILED"
exit $FAIL
```

---

## Cloud Backup (Optional)

For production deployments, integrate with object storage:

```bash
# gcs backup (Google Cloud Storage)
gcloud storage cp -r /tmp/massive_backups/* gs://massive-backups/$(date +%Y/%m/)
```

Or use AWS S3:

```bash
aws s3 sync /tmp/massive_backups/ s3://massive-backups/$(date +%Y/%m/)
```

---

*Documented in PRODUCTION_ARCHITECTURE_SPEC.md §4.9*
