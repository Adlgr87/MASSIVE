# MASSIVE — Agent Memory

## Project layout (key paths)
- `api.py` — FastAPI entrypoint; endpoints at `/api/*` (extract, wizard, simulate-uil) + `/health`, `/ready`, `/version`.
- `services/` — thin service layer over core engines. Exports `run_scalar_simulation`, `run_multilayer_simulation`, `forecast_service`, `factbook_service`, `llm_service` (see `__init__.py`).
- `backend/app/models/` — pydantic v2 DTOs (`extra="forbid"`). Namespace re-export at `backend.app.models.__init__`.
  - `dto_architect.py`        → InterventionRecord, InterventionLogEntry, ArchitectEventMessage
  - `dto_forecast.py`         → ForecastPoint, Feasibility, ForecastResponse
  - `dto_simulation.py`       → SimAgentLite, SimAggregateMetrics, SimSnapshotMessage, SimEventMessage, SimMode, SimEventKind, SimulationSnapshotPayload
  - `dto_snapshot.py`         → SnapshotRecord, TimelineTick, TimelineResponse
- Core engines (root-level modules, importable directly):
  - `social_architect.py` → `buscar_estrategia_inversa(...)` (inverse-strategy architect), returns `(estrategia, narrativa, intentos, historial)`.
  - `forecast/engine.py` → `forecast(simulation_state, temporal_config, mode="analytical|monte_carlo", n_runs=...)` → `ForecastResult`.
  - `energy_runner.py` → `run_energy_simulation(user_goal, n_agents=50, steps=100, connectivity=0.3, range_type="bipolar", seed=42, config_overrides=None, ...)`. `energy_engine.py` has `SocialEnergyEngine`.
  - `simulator.py` → `simular`, `DEFAULT_CONFIG`, `resumen_historial`.

## Conventions
- Existing API endpoints use raw `dict` payloads (not pydantic input DTOs) + `_rate_limit(request)`, `Depends(get_api_key)`, and `_public_error(exc)` to avoid leaking internals.
- New `/api/v1/*` endpoints should follow the same pattern.
- DTOs are used for *output validation* (e.g. forecast point validated via `ForecastPoint`/`Feasibility`).

## Gotchas
- The names `architect_inverse`, `generate_forecast`, `energy_landscape`, `simulate_engine` do **not** exist in the codebase. Use the real functions listed above.
- `services/forecast_service.py` has `baseline_forecast`/`walk_forward_evaluate` (baselines only) — the full forecast engine lives in `forecast/engine.py`.

## Production Architecture Spec

`PRODUCTION_ARCHITECTURE_SPEC.md` defines the official production architecture (logical layers, v1 API contract, CLI/UI clients, `.env.example` policy, error + logging standards, and the v0.1–v0.3 roadmap). Key gap to close in **Phase 1**: `backend/app/main.py` does **not** exist yet — migrate endpoints from `api.py` → `/v1/*` and add CLI entry-points to `pyproject.toml [project.scripts]`.

## Docker (Phase 4 — multi-stage + nginx)
- `Dockerfile`: 3-stage build
  - Stage `builder-py` (python:3.11-slim): builds wheels once → `/wheels`.
  - Stage `builder-fe` (node:20-alpine): `npm ci` + `npm run build` of React/Vite frontend → `/src/dist`.
  - Stage `runtime` (python:3.11-slim): installs from wheels (no runtime network), adds nginx + supervisor, copies frontend `dist` to `/usr/share/nginx/html`. Runs **supervisord** as `appuser` managing: `api` (uvicorn, 127.0.0.1:8000), `streamlit` (8501), `nginx` (80). Runs as non-root.
- `nginx.conf`: serves `/` from `/usr/share/nginx/html` (SPA `try_files`), proxies `/api/`, `/docs`, `/health`, `/ready`, `/version` → api_backend, `/ui/` → streamlit_backend (with Upgrade headers). Static asset caching headers.
- `supervisord.conf`: api+streamlit run as `user=appuser`; nginx as root (binds :80).
- `docker-compose.yml`: maps `80:80` (nginx), `8000:8000` (direct API), `8501:8501` (Streamlit). `.dockerignore` excludes `frontend/node_modules`, `.env`, data, etc.
- Ports: 80 (public frontend+API gateway), 8000/8501 (still exposed for direct access).

## DevOps (Fase 4 — DevOps Engineer / SRE)

### install.sh
- Created; provides commands: `install`, `install-dev`, `run`, `docker`, `clean`, `lint`, `test`, `benchmark`, `docs`.
- `install` → `pip install -e .[dev]` (editable + dev extras).
- `install-dev` → `pip install -e .[full]` (all extras including ML/SCI).
- `run` → `uvicorn backend.app.main:app --host 0.0.0.0 --port 8000` (fallback to `api:app` if main unavailable).
- `docker` → `docker compose up -d --build`.
- `test` → `PYTHONHASHSEED=42 python -m pytest tests/ -q --tb=short`.
- `benchmark` → `python -m benchmarks.runner --offline --out reports/validation/ci --seed 42`.

### Packaging
- `pyproject.toml [project.scripts]`: `massive-cli = "massive.cli.main:main"` CLI entry-point added.
- CLI subcommands: `simulate`, `scientific`, `benchmark`, `forecast`, `version`, `serve`.
- `backend/app/main.py`: new FastAPI entry migrating `/v1/*` endpoints from `api.py`; `backend/app/routers/` (sim, forecast, energy, architect, benchmark) + `backend/app/security.py` + `backend/app/settings.py`.

### CI/CD (`.github/workflows/`)
- `lint.yml` — ruff + black + isort on Python; eslint on frontend.
- `frontend-build.yml` — build frontend (Vite) + type check.
- `benchmark.yml` — runs PVU-BS benchmark (offline by default) on push to main + manual dispatch (offline/llm).
- `publish.yml` — builds sdist/wheel + Docker image; publishes to PyPI + GHCR on version-tag or successful main build; conditional on all prior jobs passing.

### Dependency profiles
- `requirements.txt` mirrors `pyproject.toml` but is flat (no extras). Both used — requirements.txt for fast CI installs, pyproject.toml for install.sh.

## System Maps (Fase 0 — Cartógrafo del Sistema)

- `MASSIVE_SYSTEM_MAP.md` — mapa completo del sistema: diagrama de capas (interfaz, núcleo científico, datos, UI, infraestructura), flujos de trabajo (legacy, científico, Factbook, benchmarks), relación backend FastAPI / UI-NG / motores de simulación.
- `configs/llm_contract/massive_llm_contract.json` — contrato LLM: core_apis (13, incluye POST /v1/llm/run_simulation), user_intent_to_config (7 ejemplos NL→config), llm_guidelines (11 reglas), supported_countries, simulation_modes, plus supported_flows, llm_requested_fields, llm_output_fields, rate_limit_tiers, llm_endpoint (v1.1.0).
- `backend/app/routers/llm.py` — router `POST /v1/llm/run_simulation` (auth + rate-limit, ambiguity→422, LLM-key-missing→503). Registrado en `backend/app/main.py`.
- `services/llm_orchestrator.py` — orquestador: `classify_motor`, `run_llm_simulation`, dispatcher multi-motor, narración. Re-exportado en `services/__init__.py`.
- `backend/app/models/dto_llm.py` — DTOs `LLMRunRequest`/`LLMRunResponse`/`LLMAmbiguityResponse` (extra="forbid").
- `docs/LLM_PROMPTS.md` — plantillas de prompts RT/WC/NR/AC; `docs/MASSIVE_LLM_INTERFACE.md` — documentación completa de la interfaz LLM.

## Simulation Scientist Notes (Brexit 2016)

### Engine APIs
- `run_scientific_simulation(estado_inicial, escenario="campana", pasos=N, scientific_config={"enable_scientific_report": True})` returns `ScientificSimulationResult` with `.history`, `.summary`, `.scientific_report`, `.scientific_config`.
- `SparseMultilayerEngine(layers=[LayerState(...)], interaction_matrix, max_iterations, convergence_threshold)` from `massive_core.numerics.multilayer_engine_sparse`. Uses `LayerState(node_features, graph_adjacency, layer_id, agent_types)`.
- `SocialEnergyEngine(range_type="bipolar", temperature, lambda_social, gini_coefficient, inequality_factor, seed)` from `energy_engine`. `step(opinions, adj, attractors, repellers, eta)` returns updated opinions.
- `SparseEnsembleKalmanFilter(n_ensemble, n_state_dim, n_obs_dim, observable_indices, observation_covariance, inflation, rng)` from `massive_core.data_assimilation.kalman`. Does NOT accept `seed` or `process_covariance` as arrays (the `or` check fails on numpy arrays).
- `MultilayerEngine(N, layer_weights, coupling, dt, range_type, seed, ...)` from `multilayer_engine`. `.run(steps=N)` returns list of state arrays.

### Bipolar Opinion Encoding
- Leave = +1, Remain = -1. To convert Leave% to bipolar opinion: `opinion = 2 * leave_pct - 1`. To convert back: `leave_pct = (opinion + 1) / 2`.
- UK 2016 Brexit: T0 polling ~41% Leave, actual result 51.89% Leave.

### Output Files
- Scientific report: `/tmp/simulation_analysis_report.md`
- Residuals CSV: `/tmp/cfc_training_data/residual_timeseries.csv`
- Residual stats: `/tmp/cfc_training_data/residual_stats.json`

## CfC calibration (2026-08-17)
- **Task:** Trained a Closed-form Continuous-time (CfC) residual-correction network to correct Brexit 2016 simulation residuals from `energy_engine.py` (Langevin dynamics).
- **Environment:** Use system `python3` (torch 2.11.0 + torchdiffeq 0.2.5 installed on system Python); the MASSIVE `.venv` does **not** have torch. Activate with `source .venv/bin/activate` only works if deps are installed — prefer system python3 for CfC training. No CUDA in this environment (CPU-only).
- **Data sources:** `/tmp/cfc_training_data/residual_timeseries.csv` (366 steps), `/tmp/cfc_training_data/residual_stats.json`, `/tmp/historical_research/{initial_state,event_metadata,adjacency_matrix}.json`.
- **Existing CfC code:** `cfc_engine.py` (CfCCell, CfCRegimeSelector, CfCTauMatrix, CfCArchitectPolicy), `cfc_trainer.py` (regime/tau dataset generation + training), `cfc_router.py` (singleton router with transparent fallback). The new residual corrector follows the same τ-dynamic ODE cell pattern.
- **Output artifacts:** `/home/adlg/MASSIVE/models/cfc_calibrated/{cfc_residual.pt, config.json, training_log.json, predictions.npz, checkpoints/checkpoint_ep*.pt}`. Report: `/tmp/cfc_training_report.md`. Calibration doc: `/home/adlg/MASSIVE/calibration_log.md`.
- **Result:** ~27% RMSE reduction on test split (0.0517 → 0.0376 MAE 0.0365), val MSE 0.000371, early-stopped at epoch 34, 9.2s training.
- **Integration:** extend `CfCRouter` with `correct_residual(...)` that loads `cfc_residual.pt` and adds `r̂(t)` to the energy-engine output `ŷ(t)` → `final(t)=ŷ(t)+r̂(t)`; mirror transparent-fallback pattern (skip correction if torch/model missing). See `calibration_log.md` §6.

## Performance Benchmarking

The scalability benchmark script is at `/home/adlg/MASSIVE/benchmark_scalability.py`:
- **Engines tested**: EnergyEngine (Langevin 1D), SparseMultilayerEngine, MassiveEngine (LOD), MultilayerEngine (dense)
- **Population sizes**: 1K, 10K, 100K, 1M, 10M, 100M (adaptive steps: 365 for ≤1M, 100 for 10M, 10 for 100M)
- **Metrics collected**: wall-clock time, peak RSS (psutil), average CPU %, tracemalloc peak, throughput (agents/s), time per step
- **Output files**:
  - `/tmp/performance_metrics/performance_benchmarks.json` — full structured results
  - `/tmp/performance_metrics/benchmark_timeseries.csv` — per-iteration timeseries data
  - `/tmp/performance_metrics/benchmark_log.txt` — human-readable log
  - `/tmp/performance_report.md` — comprehensive performance report with projections

### Key findings:
- **Fastest at scale**: MassiveEngine (LOD) — 100M agents in 43.6s, 8.3 GB RAM
- **Fastest per-step**: EnergyEngine — 10.6M agents/s throughput at 10M agents
- **Dense MultilayerEngine**: OOMs above 10K agents (O(N²) memory)
- **8B agents projection**: MassiveEngine ~1.5 hours / 0.65 TB; EnergyEngine ~48 hours / 1.3 TB
- **No CUDA** in environment — all engines ran on CPU (numpy backend)

### Running the benchmark:
```bash
cd /home/adlg/MASSIVE && python3 benchmark_scalability.py
```

## Performance & Scalability Benchmarks (2026-08-17)

### Engine Comparison

| Engine | Max Tested | Best Time | Peak RAM | Throughput (agents/s) |
|--------|-----------|-----------|----------|----------------------|
| EnergyEngine | 10M | 110.7s@10M | 1.69 GB | 9.0M |
| SparseMultilayer | 10M | 91.9s@10M | 2.57 GB | 10.9M |
| MassiveEngine (LOD) | **100M** | 43.6s@100M | 8.34 GB | **68.7M** |
| MultilayerEngine (dense) | 10K | 10.2s@10K | 6.98 GB | 359K |

### Earth Population (8B) Projection
- **MassiveEngine (LOD)**: ~1.5 hours, 0.65 TB RAM — most feasible
- **EnergyEngine**: ~48 hours, 1.3 TB RAM — needs distributed
- **MultilayerEngine (dense)**: ~367 days, 5,450 TB RAM — infeasible (O(N²))

### Benchmark Artifacts
- Script: `/home/adlg/MASSIVE/benchmark_scalability.py` (reusable, self-contained)
- JSON: `/tmp/performance_metrics/performance_benchmarks.json`
- CSV: `/tmp/performance_metrics/benchmark_timeseries.csv`
- Report: `/tmp/performance_report.md`

### Key Learnings
1. MassiveEngine's LOD (M=√N super-agents) enables 100M agent runs
2. EnergyEngine needs distributed compute for planetary scale (>100M)
3. MultilayerEngine (dense) doesn't scale beyond 10K (memory bound)
4. No CUDA available — all GPU code falls back to CPU numpy
