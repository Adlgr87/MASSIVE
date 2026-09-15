# Archived Docker Examples

⚠️ **DEPRECATED — reference only.** The files in this directory are legacy
single-service Docker variants kept for historical reference.

## Canonical deployment

The canonical Docker deployment uses:

| File | Role |
|------|------|
| `Dockerfile` | Multi-stage build (builder-py → builder-fe → runtime) |
| `docker-compose.yml` | Canonical compose: nginx :80 + direct API :8000 |

```bash
cp .env.example .env
docker compose up -d --build
```

## Archived variants

| File | Notes |
|------|-------|
| `Dockerfile.optimized` | Legacy single-container build (no nginx/supervisord) |
| `docker-compose.single.yml` | Runs against `Dockerfile.optimized`; served API+UI on :8000 only |

These were previously the "single-service" path. Prefer the canonical pair
above for all new deployments.
