# Changelog

All notable changes to **MASSIVE** are documented here. This project follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) semantics.

## [Unreleased] — production-readiness hardening (2026-08-20)

### Added
- **Professional README rewrite** (EN + ES, verified 2026-08-20): accurate
  quick start (canonical API + CLI + Docker, all commands executed against a
  real uvicorn server), verified route inventory from OpenAPI, Mermaid
  architecture diagram, "why it's different" frontier table (LOD population
  scale, LLM-as-math-translator contract, CfC residual correction, EnKF
  assimilation, scientific opt-in layer, inverse design, Rust kernels),
  quality/production-posture table, repository layout and full documentation
  index. Replaces the stale quickstart (`app.py` never existed) and
  de-duplicated endpoint tables.
- **`GET /metrics`** on the canonical backend: dependency-free Prometheus
  text format — `http_requests_total{method,group,status}` counter (recorded
  by the request middleware, path groups llm/simulate/forecast/engine/
  benchmarks/infra/other) and `massive_uptime_seconds` gauge.
- Request body-size guard: requests whose declared `Content-Length` exceeds
  `MASSIVE_MAX_BODY_MB` (default 10 MB) are rejected with 413 before any
  handler work — previously only file uploads were size-limited.
- Request correlation & access logging in the canonical backend: every
  response carries `X-Request-ID` (echoed when the client supplies it) and a
  single structured access line (`request_id/method/path/status/duration_ms`).
- `Makefile` with verified developer targets (`install/test/test-cov/lint/
  format/typecheck/api/frontend-*/benchmark`).
- `tests/test_backend_observability.py` (5 tests) covering request-id
  propagation and readiness semantics.

### Changed
- **`/ready` semantics (Hito 4)**: readiness now depends only on REQUIRED
  dependencies (typed settings + simulation core import). Missing LLM
  credentials no longer 503 the whole probe — the API answers
  `200 {"mode": "degraded"}` because core endpoints work without LLMs
  (`/v1/llm/*` degrades itself with 503). Load balancers keep routing
  traffic to a fully-functional core.
- Coverage measurement scope now includes `backend/`, `forecast/` and `api`
  (`[tool.coverage.run] source`); measured baseline: **68%** branch coverage
  (6 476 stmts).

### Removed
- 16 orphaned UI-NG modules from the root backend (PR #84 residue, verified
  unreachable from `backend.app.main` and unimported by tests): evaluation.py
  (+eval_golden.json), live_runner.py, llm_chat.py, llm_prompts.py, metrics.py,
  narrative.py, rate_limit.py, run_store.py, scenario_parser.py, routers
  conversation/live/simulation/status, models/dto_ui, services/. The kit keeps
  its own copies under `massive-ui-ng/backend/`.

### Fixed
- Tests no longer dirty the working tree: the Factbook validation-report test
  writes to pytest `tmp_path` instead of `reports/factbook_validation_*.json`.
- **TEST-01 (blocker)**: `tests/test_llm_endpoint.py` and
  `tests/test_llm_orchestrator_coverage.py` were rewritten by PR #84 against a
  `create_app` factory + `classified_motor` contract that never existed in the
  shipped `backend/app` (UI-NG draft divergence) and failed at import. Both
  modules now validate the canonical contract v1.1.0
  (`configs/llm_contract/massive_llm_contract.json`): response envelope
  `sim_id/motor/config/summary/narrative/results/assumptions/factbook_params`,
  ambiguity 422 with `requested_fields`, LLM-required 503, strict
  `extra=forbid` DTO, auth 401, and offline (no-LLM) dispatch per motor family
  with seed reproducibility.
- **TEST-02**: `test_estimate_intervention_cost` passed a 1-D array to
  `estimate_intervention_cost`, whose documented contract is a
  `(n_phases, n_agents)` matrix. Fixture fixed (+seeded RNG); function untouched.
- **TEST-03**: `test_describe_families_smoke_4clusters` used 20 sims while the
  KMeans fallback caps `k ≤ n_sims//10 = 2`, making k=4 unreachable. Fixture
  now builds 60 sims (4×15); verified silhouette picks k=4 (0.952). Engine
  behavior unchanged.
- **FE-01 (blocker)**: `frontend/vite.config.ts` lacked the `@ → ./src`
  resolve alias (tsconfig had it), so `npm run build` failed on
  `@/components/ui/button`. Build is green again (41 modules) — this also
  unblocks the Frontend CI and Docker image build.
- **SEC-02**: `api.py` only recognized `MASSIVE_ENV=dev` while the documented
  value is `development` (and the canonical backend defaulted to development
  when unset). New shared helper `massive_core.config.api_auth.is_dev_env`
  unifies semantics across both backends (dev alias kept, unset=development,
  staging/production fail closed). Enforced by new parity tests.
- **SEC-03**: API-key comparison now constant-time (`hmac.compare_digest`)
  in both `api.py` and `backend/app/security.py` via shared
  `api_key_matches`.
- **LINT-01**: ruff (28 errors), black (2 files) and mypy slice (1
  `attr-defined` in `services/llm_orchestrator.py`) are clean again.
- **DOCS-01**: README Quick Start referenced a non-existent `app.py`
  (Streamlit UI removed from the repo long ago); replaced with the real
  `uvicorn` commands (legacy `api:app` and canonical `backend.app.main:app`).
- **OPS-02**: container stack started a phantom `streamlit` program (binary
  not installed in the image → eternal respawn loop), exposed port 8501 and
  an nginx `/ui/` route to a dead upstream. Removed from
  `supervisord.conf`/`Dockerfile`/`docker-compose.yml`/`nginx.conf`.

### Removed
- Junk files from the Zapier-token incident: `0`, `test-zapier.txt`,
  `.github/test-zapier-dir.txt`; stale `README.backup.md`.
- Tracked MkDocs build output `site/` (84 files, ~6.5 MB) — regenerated by the
  `Docs Deploy` workflow; now gitignored.

### Security
- **SEC-01 (requires owner action)**: a Zapier MCP token (108 chars) remains
  recoverable from public git history (commit `dc2240c`, file
  `.codebuff/config.json`, deleted later in PR #81 without rotation). It must
  be considered compromised and rotated at the provider. Documented in
  `docs/security/threat-model.md` and `docs/production-readiness-audit.md`.

### Tests
- Full suite now collects and passes with **no exclusions**: 521 tests green
  (~35 s, 2 vCPU sandbox), including the two previously-broken modules and 8
  new auth-parity/security tests.

### Documentation
- Added production-readiness deliverables: `docs/production-readiness-audit.md`
  (risk matrix + milestone plan), `docs/architecture/current-state.md` and
  `target-state.md`, `docs/runbooks/{local-development,operations,incidents}.md`,
  `docs/security/{threat-model,secrets-and-configuration}.md`,
  `docs/testing/test-strategy.md`, `docs/performance/baseline.md`,
  `docs/release-checklist.md`.

## [Unreleased] (post-PR #79)

### Security
- **SEC-01**: Replace weak `change-me` API key placeholders in `.env.example`
  with a generated strong token (`secrets.token_urlsafe(32)`) and document
  key-rotation instructions.
- **SEC-02**: `api.py` root auth now returns **503 ServiceUnavailable** when no
  API key is configured instead of leaking an empty-credentials error.

### Performance
- **PERF-01**: `MultilayerEngine.run()` accepts `store_history=False` and emits
  compact per-step aggregates instead of full `(N, K)` snapshots — from
  `O(steps·N·K)` to `O(steps·4)` memory. Service layer (`run_multilayer_simulation`)
  defaults to the compact path. `MassiveSimEngine.run()` accepts the flag for
  signature symmetry (its LOD engine already stores only weighted means).

### Observability
- **OBS-01**: Add `MultilayerEngine.diagnose()` returning `{n_agents, n_features,
  n_steps_recorded, state_bytes, opinion_mean/_std/_min/_max}`. The service
  layer surfaces these under a `diagnostics` key. `MassiveSimEngine` already
  exposes `memory_report` plus `elapsed_seconds`/`steps_per_second` in its
  result dict.

### Tests
- Baseline verified green: **446 passed, 20 skipped** (skips are PyTorch/GPU
  env-gated). No regressions from Phases B–E.

## [v1.1] — prior productionization release (PR #79)
- See release notes for full list.
