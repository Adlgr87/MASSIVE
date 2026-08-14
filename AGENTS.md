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
