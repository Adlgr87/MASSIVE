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

## Docker (Phase 4 — multi-stage + nginx)
- `Dockerfile`: 3-stage build
  - Stage `builder-py` (python:3.11-slim): builds wheels once → `/wheels`.
  - Stage `builder-fe` (node:20-alpine): `npm ci` + `npm run build` of React/Vite frontend → `/src/dist`.
  - Stage `runtime` (python:3.11-slim): installs from wheels (no runtime network), adds nginx + supervisor, copies frontend `dist` to `/usr/share/nginx/html`. Runs **supervisord** as `appuser` managing: `api` (uvicorn, 127.0.0.1:8000), `streamlit` (8501), `nginx` (80). Runs as non-root.
- `nginx.conf`: serves `/` from `/usr/share/nginx/html` (SPA `try_files`), proxies `/api/`, `/docs`, `/health`, `/ready`, `/version` → api_backend, `/ui/` → streamlit_backend (with Upgrade headers). Static asset caching headers.
- `supervisord.conf`: api+streamlit run as `user=appuser`; nginx as root (binds :80).
- `docker-compose.yml`: maps `80:80` (nginx), `8000:8000` (direct API), `8501:8501` (Streamlit). `.dockerignore` excludes `frontend/node_modules`, `.env`, data, etc.
- Ports: 80 (public frontend+API gateway), 8000/8501 (still exposed for direct access).
