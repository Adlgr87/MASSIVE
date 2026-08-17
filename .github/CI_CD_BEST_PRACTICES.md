# CI/CD Best Practices Applied

This document captures the CI/CD best practices applied to the MASSIVE project
in Phase 4 (DevOps Engineer / SRE), based on industry-standard patterns for
Python + FastAPI + Docker ML projects (GitHub Actions, PyPI, GHCR).

## 1. Job Isolation & Dependency Ordering (publish.yml)

```
lint → [test, frontend-build, benchmark, docs] → build-wheels → build-image
                       ↓
              publish-pypi / publish-docker (on release or tag)
```

- **Separate jobs** for each concern (lint, test, frontend, benchmark, docs).
- **`needs:`** chains enforce ordering without blocking unrelated jobs.
- **Conditional publish** only on `release` event or `refs/tags/*` — not on every `main` push.
- Build on `main` always happens (no push).

## 2. Caching

| Artifact | Cache key |
|----------|-----------|
| pip dependencies | `pip-${{ runner.os }}-python-3.11-${{ hashFiles('requirements.txt') }}` |
| npm dependencies      | `npm-${{ hashFiles('frontend/package-lock.json') }}` |
| Docker layer cache    | `type=gha` (GitHub Actions cache) |
| ruff/mypy cache       | Not needed (fast) |

## 3. Reproducibility

- `PYTHONHASHSEED=42` set in all test/benchmark jobs (per ADR-003).
- Seeds passed explicitly to `benchmarks.runner --seed 42`.
- Docker image tagged with both `sha` and `semver` tags.

## 4. Security

- **`GITHUB_TOKEN`** used for registry auth (auto-provisioned by Actions).
- **Secrets** (`OPENAI_API_KEY`, etc.) never echoed — only passed as env.
- **Security scan** (`secret_scan.yml` via gitleaks) runs on every PR/push.
- **No secrets in Docker images** — `.env*` files mounted as volumes.
- **Non-root user** in Docker (`appuser`).
- **`id-token: write`** only on publish jobs (OIDC trust for PyPI Trusted Publishing).

## 5. Fail-Fast & Observability

- **Healthcheck** in Docker Compose + GitHub Actions waits for `/health`.
- **Artifacts** uploaded on every job (`always()`), even on failure.
- **Timeouts** set on long-running jobs (benchmarks: 30 min).
- **Continue-on-error** for informational jobs (coverage snapshot in pytest.yml).

## 6. Frontend CI

- **Type check** (`tsc --noEmit`) before build — catches type drift early.
- **Build** produces `dist/` artifact — consumed by Docker build.
- **ESLint + Prettier** via `npm run lint`.
- **No secrets** required for build — only for optional LLM features.

## 7. Publish gates

The `publish.yml` workflow uses a **fan-in gate pattern**:

```
build-wheels  (needs: lint, test, benchmark, docs)
build-image   (needs: lint, test, frontend-build, benchmark, docs)
publish-pypi  (needs: build-wheels)   ← only on release/tag
publish-docker (needs: build-image)   ← only on release/tag
```

This ensures **both PyPI and Docker are only published when ALL checks pass**.
The `build-only-main` job builds the image on every main push (no push)
to catch regressions early.

## 8. Branch protection

Recommended branch protection rules on `main`:
- Require status checks: `lint`, `test`, `frontend-build`, `benchmark`, `docs`
- Require up-to-date branches
- Include administrators
