# Disaster Recovery Plan for MASSIVE UIL API

**Version 1.0** | **Scope:** backend.app.main:app production deployment

## RTO/RPO Targets

| Metric | Target | Rationale |
|--------|--------|-----------|
| Recovery Time Objective (RTO) | 30 minutes (active→warm) | CI/CD + Docker image rebuild |
| Recovery Point Objective (RPO) | 5 minutes | Factbook DB snapshots every 5 min |
| MTTR | < 15 minutes (common failure) | Automated rollbacks |

## Recovery Scenarios

### 1. Stateless API Container Failure
**Detection:** `/health` or `/ready` probe fails; Kubernetes/Docker restart policy kicks in.
**Action:** 
1. Container restarts automatically (restart: unless-stopped)
2. If restart succeeds → service restored (RTO: 0)
3. If restart fails → rollback to previous image (`docker compose down && git checkout HEAD~1 && docker compose up -d --build`)

### 2. Factbook Database Corruption
**Detection:** `/ready` check fails with "database" in error message; queries return SQL errors.
**Action:**
1. Deploy from latest snapshot: `/db/snapshots/factbook_$(date +%Y%m%d_%H%M).sql`
2. `pg_restore --clean --if-exists -d factbook /db/snapshots/factbook_*.sql`
3. Verify: `pg_isready -d factbook`

### 3. Model Artifact Loss (cfc_*.pt)
**Detection:** `/ready` reports `residual_corrector: False`; simulations fail to apply corrections.
**Action:**
1. Restore from Git LFS or artifact store: `gs://massive-models/cfc_calibrated/`
2. Retrain if unavailable: `python3 train_cfc_lambda.py && python3 train_cfc_temp.py && python3 train_cfc_landscape.py`
3. RTO for restore: ~2 min; RTO for retrain: ~30 min

### 4. Total Region Outage
**Detection:** All health checks fail; load balancer marks service down.
**Action:**
1. Failover to secondary region: `terraform workspace select backup`
2. Promote read replica: `gcloud sql instances patch factbook-backup --activation-policy=ALWAYS`
3. DNS failover: TTL=60s; update A-record to backup region IP

## Backup Strategy

| Data | Frequency | Retention | Location |
|------|-----------|-----------|----------|
| Factbook DB snapshots | 5 minutes | 24 hours | `gs://massive-backups/db/` |
| Model weights (cfc_*.pt) | On training completion | Indefinite | Git LFS + `gs://massive-models/` |
| Simulation history | Daily batch | 30 days | `gs://massive-backups/simulations/` |
| Configuration (.env, configs/) | On change (Git) | Permanent | Repository |

## Testing

- **Monthly:** DR drill — restore from latest Factbook snapshot
- **Quarterly:** Failover to backup region (non-disruptive)
- **Post-deployment:** `scripts/security_audit.sh` + `pytest tests/`

## Contacts

| Role | Contact |
|------|---------|
| Primary On-Call | SRE rotation: sre@massive.ai |
| Secondary | DevOps lead: devops@massive.ai |
| Security | security@massive.ai |
