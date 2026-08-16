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
