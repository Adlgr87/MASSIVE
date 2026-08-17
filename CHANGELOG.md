# Changelog

All notable changes to **MASSIVE** are documented here. This project follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) semantics.

## [Unreleased]  (post-PR #79)

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
