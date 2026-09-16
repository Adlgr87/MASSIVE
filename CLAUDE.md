# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

## MASSIVE-specific conventions

- JIT-compiled kernels accept only plain numpy arrays — no dicts, DataFrames, or Python objects.
- All opinion values stay within their declared range (unipolar `[0,1]` or bipolar `[-1,1]`); use `np.clip` after every update.
- The main simulation API (`simular`, `simular_multiples`) must remain backward-compatible. New features live in new modules.
- New modules follow the existing docstring style (Google-style with Args/Returns).
- Build: `pip install -r requirements.txt` · Run: `uvicorn backend.app.main:app --host 0.0.0.0 --port 8000` · Test: `pytest tests/`

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

<!-- This file consolidates AGENTS.md (referenced as the canonical agent memory). -->

## MASSIVE Agent Memory (from AGENTS.md)

### Project layout (key paths)
- `api.py` — FastAPI entrypoint; endpoints at `/api/*` (extract, wizard, simulate-uil) + `/health`, `/ready`, `/version`.
- `services/` — thin service layer over core engines. Exports `run_scalar_simulation`, `run_multilayer_simulation`, `forecast_service`, `factbook_service`, `llm_service` (see `__init__.py`).
- `backend/app/models/` — pydantic v2 DTOs (`extra="forbid"`). Namespace re-export at `backend.app.models.__init__`.
  - `dto_architect.py`        → InterventionRecord, InterventionLogEntry, ArchitectEventMessage
  - `dto_forecast.py`         → ForecastPoint, Feasibility, ForecastResponse
  - `dto_simulation.py`       → SimAgentLite, SimAggregate, SimSnapshotMessage, SimEventMessage, SimMode, SimEventKind, SimulationSnapshotPayload
  - `dto_snapshot.py`         → SnapshotRecord, TimelineTick, TimelineResponse
- Core engines (root-level modules, importable directly):
  - `social_architect.py` → `buscar_estrategia_inversa(...)` (inverse-strategy architect), returns `(estrategia, narrativa, intentos, historial)`.
  - `forecast/engine.py` → `forecast(simulation_state, temporal_config, mode="analytical|monte_carlo", n_runs=...)` → `ForecastResult`.
  - `energy_runner.py` → `run_energy_simulation(user_goal, n_agents=50, steps=100, connectivity=0.3, range_type="bipolar", seed=42, config_overrides=None, ...)`. `energy_engine.py` has `SocialEnergyEngine`.
  - `simulator.py` → `simular`, `DEFAULT_CONFIG`, `resumen_historial`.

### Conventions
- Existing API endpoints use raw `dict` payloads (not pydantic input DTOs) + `_rate_limit(request)`, `Depends(get_api_key)`, and `_public_error(exc)` to avoid leaking internals.
- New `/api/v1/*` endpoints should follow the same pattern.
- DTOs are used for *output validation* (e.g. forecast point validated via `ForecastPoint`/`Feasibility`).

### Gotchas
- The names `architect_inverse`, `generate_forecast`, `energy_landscape`, `simulate_engine` do **not** exist in the codebase. Use the real functions listed above.
- `services/forecast_service.py` has `baseline_forecast`/`walk_forward_evaluate` (baseline only) — the full forecast engine lives in `forecast/engine.py`.

### Production Architecture Spec
`docs/architecture/PRODUCTION_ARCHITECTURE_SPEC.md` defines the official production architecture (logical layers, v1 API contract, CLI/UI clients, `.env.example` policy, error + logging standards, v0.1–v0.3 roadmap). Key gap to close in Phase 1: `backend/app/main.py` does **not** exist yet — migrate endpoints from `api.py` → `/v1/*` and add CLI entry-points to `pyproject.toml [project.scripts]`.

### Docker (Phase 4 — multi-stage + nginx)
- `Dockerfile`: 3-stage build (builder-py → builder-fe → runtime).
- `docs/architecture/PRODUCTION_ARCHITECTURE_SPEC.md` §5: nginx serves `/` from `/usr/share/nginx/html`, proxies `/api/`, `/docs`, `/health`, `/ready`, `/version` → api_backend, `/ui/` → ui component_backend.
- `docker-compose.yml`: maps `80:80` (nginx), `8000:8000` (direct API), `8501:8501` (ui component).

### DevOps
- `install.sh`: commands `install`, `install-dev`, `run`, `docker`, `clean`, `lint`, `test`, `benchmark`, `docs`.
- `run` → `uvicorn backend.app.main:app --host 0.0.0.0 --port 8000` (fallback to `api:app` if main unavailable).
- Build: `pip install -r requirements.txt` · Run: `uvicorn backend.app.main:app` · Test: `pytest tests/`

### Simulation Scientist Notes (Brexit 2016)
**Engine APIs:** `run_scientific_simulation(...)` → `ScientificSimulationResult`; `SocialEnergyEngine(...)` from `energy_engine`; `MultilayerEngine(...)` from `multilayer_engine`.

**Bipolar Opinion Encoding:** Leave = +1, Remain = -1. `opinion = 2 * leave_pct - 1`; `leave_pct = (opinion + 1) / 2`. UK 2016: T0 ~41% Leave, actual 51.89%.

**Output Files:** Scientific report → `reports/simulation_analysis_report.md`; Residuals CSV → `reports/cfc_training/residual_timeseries.csv`.

### CfC calibration (2026-08-17)
- Trained CfC residual-correction network. Output artifacts in `models/cfc_calibrated/`. Report: `reports/cfc_training_report.md`. Calibration doc: `docs/research/calibration_log.md`.
- Integration: extend `CfCRouter` with `correct_residual(...)` — loads `cfc_residual.pt`, adds r̂(t) to engine output ŷ(t).

### Key file references
- Production architecture spec: `docs/architecture/PRODUCTION_ARCHITECTURE_SPEC.md`
- System map: `docs/architecture/MASSIVE_SYSTEM_MAP.md`
- Calibration log: `docs/research/calibration_log.md`
- W4 audit workflow: `docs/archive/AUDIT_REMEDIATION_WORKFLOW.md`

---

## RECOVERY RECORD — MASSIVE Recovery Plan (autogenerado)

- Backup branch created (local): backup/pre-recovery-20260527
- HEAD SHA at backup: 23b4bf3692f7c9985ea57c35fcdc02164107d486
- Fecha inicio: 2026-05-27T00:26:44-04:00

Fases ejecutadas:
1) Fase 1 — Análisis: detección de línea truncada en requirements.txt y necesidad de registro en CLAUDE.md.
2) Fase 2 — Reparación: (en progreso) aplicar cambios atómicos y ejecutar tests.

Reglas de seguridad aplicadas:
- No se usa push --force ni reescritura de historial.
- Todas las reparaciones serán atómicas y documentadas aquí.

Checklist post-repair:
- Ejecutar: pip install -r requirements.txt
- Ejecutar tests: pytest tests/
- Registrar resultados aquí con SHA del commit.
