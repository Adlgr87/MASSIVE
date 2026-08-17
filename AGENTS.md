# AGENTS.md — MASSIVE repository conventions

## Project
**MASSIVE** — Multi-Agent Social Simulator for Interactive Value Exploration.
Angular "next-gen" UI (renamed from the former `massive-ui-ng-package`).

## Layout
- Repository root: `backend/app/`, `frontend/`, `massive/`, `data/`.
- The Angular UI-NG source lives **only** under `massive-ui-ng/` (single source of
  truth). The standalone `massive-ui-ng-package/` directory is a throwaway test
  harness that mirrors `massive-ui-ng/` — do **not** treat it as official. All
  real work (frontend `src/`, backend `app/`, infra docker-compose, Dockerfile.ui-ng)
  happens in `massive-ui-ng/`.
- FastAPI backend lives inside `massive-ui-ng/backend/app/` (merged from root). Run:
  ```
  uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
  ```
  from `massive-ui-ng/` with `PYTHONPATH=.`.
- Docker single service (`docker compose -f massive-ui-ng/infra/docker-compose.yml up --build`)
  exposes the API + compiled Angular frontend on `:8000`.

## One-command install & run
- `./install.sh` — one-shot installer: creates `.venv`, installs Python deps,
  builds the UI-NG frontend (`frontend/dist`).
- `./install.sh run` — same as install, then launches `uvicorn` on `:8000`
  serving both API and built frontend (`MASSIVE_SERVE_FRONTEND=1`).
- `./install.sh docker` — builds and runs the single-service Docker image.
- `./install.sh clean` — removes `.venv`, `node_modules`, build artifacts.

## Status
- ✅ Streamlit (`app.py`, `.streamlit/`) fully removed (T6).
- ✅ Model exports fused: `backend/app/models/dto_ui.py` (AssumptionItem,
  ConversationResponse, LLMStatus, SimulateRequest/Response, …) re-exported
  from `backend/app/models/__init__.py` (T4).
- ✅ Repo root has NO "BeyondSight" or "mamba" references (legacy removed).
- ✅ Git in sync with https://github.com/Adlgr87/MASSIVE.

## Notes / Gotchas
- Do NOT reintroduce the name `beyondsight` or `mamba`; the canonical name is
  **MASSIVE**. Revert any PR that uses the old name.
- `target/` (Rust build artifacts) is gitignored.

## Simulation engine API (Phase D/E post-PR #79)
- `MultilayerEngine.run(steps=100, store_history=True)`:
  - `store_history=False` → returns compact per-step aggregates
    `[{"mean_opinion","std_opinion","polarization","sample_size"}, …]`
    instead of full `(N, K)` snapshots.  O(steps·4) vs O(steps·N·K).
  - Use `store_history=False` in the service layer (default for
    `run_multilayer_simulation`).
- `MassiveSimEngine.run(steps, store_history=True)`:
  - LOD engine already stores only weighted-mean history; `store_history`
    is accepted for signature symmetry and ignored.
- `MultilayerEngine.diagnose() -> dict[str, float]` returns
  `{n_agents, n_features, n_steps_recorded, state_bytes, opinion_mean,
   opinion_std, opinion_min, opinion_max}` for observability hooks.
- `MassiveSimEngine.memory_report` (property) + `run()` result dict already
  carry `elapsed_seconds`, `steps_per_second`, `memory_savings_pct`.
- Auth: `api.py` root returns **503 ServiceUnavailable** when no API key is
  configured (Phase B).  Tests in `test_llm_endpoint.py` use per-request
  `api_key` body field, so unaffected.
