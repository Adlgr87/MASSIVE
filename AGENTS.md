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
