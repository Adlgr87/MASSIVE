<div align="center">

# MASSIVE

**Mathematical Architecture for Scalable Social Interaction & Virtual Engine**

*A hybrid physics + AI platform that simulates opinion formation, polarization and
intervention outcomes over complex social systems — from 10 agents to 100 million.*

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](pyproject.toml)
[![Tests](https://github.com/Adlgr87/MASSIVE/actions/workflows/pytest.yml/badge.svg?branch=main)](.github/workflows/pytest.yml)
[![Type-check: MyPy](https://github.com/Adlgr87/MASSIVE/actions/workflows/typecheck.yml/badge.svg)](.github/workflows/typecheck.yml)
[![Rust: optional](https://img.shields.io/badge/Rust-optional_acceleration-orange?logo=rust)](Cargo.toml)

[Quick start](#-quick-start) · [Architecture](#-architecture) · [API](#-http-api) · [The LLM layer](#-the-llm-layer-natural-language--mathematics) · [Benchmarks](#-benchmarks) · [Docs](#-documentation)

</div>

---

## Why MASSIVE is different

Most social simulators force a choice between scale, scientific rigor and usability.
MASSIVE is **hybrid by design** at every layer:

| Frontier | What we do | Where |
|---|---|---|
| 🌍 **Population-scale via LOD compression** | Agents with identical features collapse into *super-agents*, so **100 million agents run in ~8 GB RAM** — near-constant memory with event-driven, uint8-quantized sparse updates. | `massive_engine.py` |
| 🤖 **LLM as a *mathematical translator*, not a chatbot** | Natural language → validated simulation config under a **versioned machine contract** (v1.1.0): intent classification routes to the right engine, ambiguous requests get `422 + requested_fields`, and every run degrades **deterministically without any API key**. | `services/llm_orchestrator.py`, `configs/llm_contract/` |
| 🧠 **Liquid neural residual correction** | A Closed-form Continuous-time (CfC) network learns the *systematic bias* of the physics engine and corrects it — **50 % direction error reduction** on the Brexit referendum case (10/10 seeds improved). | `cfc_engine.py`, `models/cfc_calibrated/` |
| 📡 **Data assimilation for opinion dynamics** | Sparse Ensemble Kalman Filter fuses real-world observations into the running state, the way numerical weather prediction does. | `massive_core/data_assimilation/` |
| ⚗️ **Scientific opt-in layer** | Adaptive steppers, stability & bifurcation analysis, physics-informed neural nets, network inference and statistical mechanics — all behind explicit config flags that never alter the default dynamics. | `massive_core/` |
| 🧬 **Inverse intervention design** | Ask *"what campaign reaches this consensus?"* — the social architect searches the intervention space backwards from the goal. | `social_architect.py` |
| ⚡ **Optional Rust kernels** | Hot-path numerics compiled with pyo3/maturin, with transparent pure-Python fallbacks. | `rust_core/` → `massive_rust_core` |
| 🔬 **Validation-first culture** | Pre-registered anti-leakage protocol, seeded RNG everywhere, contract-validated APIs, 16-check CI, offline PVU benchmark suite. | `datasets/pvu_cases/`, `benchmarks/` |

---

## 🚀 Quick start

Verified from a clean clone (Python 3.11+, ~2 min install):

```bash
git clone https://github.com/Adlgr87/MASSIVE.git && cd MASSIVE
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add LLM/social API keys if you have them (optional)

# Canonical versioned API (/v1/*) — interactive docs at /docs
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

```bash
# First simulation in one command (dev mode accepts the documented fallback key)
curl -H "X-API-Key: dev-secret-key" -X POST localhost:8000/v1/simulate \
     -H 'Content-Type: application/json' -d '{"pasos": 30}'
```

Or use the CLI, no server needed:

```bash
python -m massive.cli simulate --pasos 30     # scalar engine + JSON summary
python -m massive.cli version
```

Or pure Python, zero server:

```python
from services.simulation_service import run_multilayer_simulation
result = run_multilayer_simulation(n_agents=100, steps=50, seed=42)
print(result["landscape"])
```

**Prefer Docker?**

```bash
cp .env.example .env
docker compose -f docker-compose.single.yml up -d --build   # API + UI on :8000
curl -fsS localhost:8000/health
```

> Minimum: Python 3.11, 500 MB RAM. Rust/CUDA/torch/LLM keys are all optional —
> every optional layer has a deterministic fallback.

---

## 🏗 Architecture

```mermaid
flowchart TB
    subgraph Clients
        FE["React frontend (frontend/)"]
        CLI["massive-cli"]
        AG["LLM agents / curl"]
    end

    subgraph API["FastAPI backends"]
        V1["Canonical /v1 (backend/app/)<br/>simulate · forecast · engine · benchmarks · llm<br/>typed DTOs (extra=forbid) · X-API-Key · rate limit"]
        LEG["Legacy /api (api.py)<br/>extract · wizard · simulate-uil"]
    end

    subgraph Services["services/ — orchestration boundary"]
        ORCH["llm_orchestrator<br/>NL → engine dispatch (contract v1.1.0)"]
        SIM["simulation_service"]
        FOR["forecast_service"]
        FB["factbook_service"]
    end

    subgraph Engines["Scientific engines (repo root)"]
        direction LR
        E1["simulator.py<br/>scalar legacy"]
        E2["multilayer_engine<br/>5D Langevin sociodemographic"]
        E3["massive_engine<br/>LOD super-agents (100M)"]
        E4["energy_engine<br/>social-energy SDE"]
        E5["micro_engine<br/>families of futures"]
        E6["forecast<br/>temporal risk"]
        E7["social_architect<br/>inverse interventions"]
        E8["cfc_engine<br/>liquid-NN residual corrector"]
    end

    subgraph Core["massive_core/ — opt-in scientific layer"]
        C1["adaptive steppers · stability · bifurcation"]
        C2["sparse EnKF assimilation"]
        C3["PINNs · network inference · metalearning"]
        C4["optional Rust kernels (massive_rust_core)"]
    end

    DATA["CIA World Factbook (260+ countries)<br/>demographics · Gini · GDP · diversity"]

    Clients --> API --> Services --> Engines --> Core
    FB --> DATA
    ORCH --> Engines
```

Key invariants:

- **The engines are the product** — APIs, CLI and LLM layers are thin, typed boundaries over them.
- **Optional means optional**: no Rust build, no GPU, no LLM key, no Factbook data → everything still runs deterministically (seeds + `PYTHONHASHSEED` respected).
- **Fail-closed security**: staging/production refuse to start serving without `MASSIVE_API_KEY`; the dev fallback key is loudly logged and impossible in production.

---

## 📡 HTTP API

**Canonical — `backend.app.main:app`** (recommended for new integrations)

| Endpoint | Method | Purpose |
|---|---|---|
| `/v1/simulate` | POST | Scalar simulation (history + summary) |
| `/v1/forecast` | POST | Analytical + Monte-Carlo temporal forecast |
| `/v1/engine/energy` | POST | Social-energy Langevin landscape |
| `/v1/engine/architect` | POST | Inverse intervention search |
| `/v1/benchmarks` | POST | PVU-BS offline validation run |
| `/v1/llm/run_simulation` | POST | **NL intent → engine → narrated result** (contract v1.1.0) |
| `/health`, `/ready`, `/version` | GET | Liveness · readiness (required deps only) · metadata |
| `/metrics` | GET | Prometheus counters (`http_requests_total`, uptime) |
| `/docs` | GET | Auto-generated OpenAPI UI |

**Legacy — `api.py`** (used by the React frontend; compatibility surface)

`POST /api/extract` (PDF/CSV/JSON/XLSX → config) · `POST /api/wizard` (LLM) ·
`POST /api/simulate-uil` · `POST /api/v1/{architect,forecast,energy}`

**Operational defaults**: `X-API-Key` auth (constant-time compare) · 60 req/min per IP
(`MASSIVE_RATE_LIMIT_PER_MIN`) · 10 MB body limit (`MASSIVE_MAX_BODY_MB`) ·
CORS allowlist without wildcards · upload extension allowlist ·
`X-Request-ID` correlation on every response · structured access log with duration.
Full variable reference: `.env.example` and [`docs/security/secrets-and-configuration.md`](docs/security/secrets-and-configuration.md).

---

## 🤖 The LLM layer: natural language → mathematics

`POST /v1/llm/run_simulation` turns an intent like
*"Simula el paisaje de energía social para Brasil con desigualdad"* into a seeded,
validated engine run:

1. **Classify** the intent against the machine-readable contract
   (`configs/llm_contract/massive_llm_contract.json`, v1.1.0) → engine family.
2. **Ambiguity protocol**: missing required fields (e.g. forecast horizon) →
   `422` with `requested_fields` — the agent asks the user instead of guessing.
3. **Translate** NL → config with the LLM (Groq / OpenAI / OpenRouter / Ollama) or,
   with **no key configured**, documented deterministic defaults.
4. **Augment** with CIA Factbook parameters when a country is detected (Gini →
   attractor depth, GDP → intervention budgets, diversity → social pressure).
5. **Dispatch** to the right engine; return a typed envelope
   (`sim_id · motor · config · summary · narrative · results{timeline, payload} · assumptions`).

Inherently LLM-driven flows (e.g. the inverse architect) fail closed with a clear
`503` when no key is available — never silently degraded.

---

## 📊 Benchmarks

Measured on the repo's benchmark rig (31 GB RAM — run `benchmark_scalability.py` on your own hardware):

| Engine | 1K agents | 100K | 1M | 100M |
|---|---|---|---|---|
| **MassiveEngine** (LOD aggregated) | 0.39 s · 0.87 GB | 2.3 s · 0.87 GB | 21 s · 0.88 GB | **44 s · 8.3 GB** |
| EnergyEngine | 0.06 s | 3.1 s | 35 s | 16.8 GB required |
| SparseMultilayerEngine | 0.03 s | 6.3 s | 43 s · 1.1 GB | N/A |

Reference micro-benchmarks (2 vCPU sandbox, service-layer path, min of 3):
scalar 50 steps **0.029 s** · multilayer 100×50 **0.008 s** · massive LOD 10K×50 **0.023 s** ·
energy 50×100 **0.012 s** — method in [`docs/performance/baseline.md`](docs/performance/baseline.md).

**Scientific validation**: the PVU-MASSIVE protocol runs real-case studies offline
(`python -m benchmarks.runner --cases datasets/pvu_cases --offline`), with a
pre-registration template to prevent analysis leakage. The calibrated CfC corrector
halved direction error on the Brexit case (54.5 % → 53.2 % Leave; 10/10 seeds).

---

## 🧪 Quality & production posture

| Signal | Status |
|---|---|
| Test suite | **530 tests, ~38 s**, no exclusions — `make test` / `pytest tests/` |
| Coverage | 68 % branch (scope: engines + services + backend) — `make test-cov` |
| Static quality | ruff + black + mypy (gradual slice) green in CI |
| CI | 16 checks per PR: lint, types, core/scientific/api/full suites, frontend build+lint, Docker compose health, TS-type sync, secret scan, semgrep, PVU benchmark |
| Security | fail-closed auth, rate & body limits, constant-time compares, no secrets in tree (one historical token documented + pending rotation, see `docs/security/threat-model.md`) |
| Observability | `/metrics` Prometheus, `X-Request-ID`, structured access logs, degraded-mode readiness |
| Runbooks | local dev · operations · incidents — `docs/runbooks/` |

---

## 📁 Repository layout

```
MASSIVE/
├── backend/app/          # Canonical FastAPI (/v1): routers, DTOs, security, metrics
├── services/             # Orchestration boundary (simulation, forecast, LLM, factbook)
├── massive_core/         # Opt-in scientific layer (steppers, EnKF, PINNs, config…)
├── massive/              # CLI + core/factbook (loader, mappings, validator)
├── simulator.py          # Scalar legacy engine (public API: simular, resumen_historial)
├── multilayer_engine.py  # 5D Langevin sociodemographic dynamics
├── massive_engine.py     # LOD super-agent engine (population scale)
├── energy_engine.py      # Social-energy landscape SDE (Euler–Maruyama)
├── micro_engine.py       # Small groups, families of futures, bifurcation analysis
├── social_architect.py   # Inverse intervention strategy search
├── forecast/             # Temporal risk forecasting
├── cfc_*.py              # CfC (liquid NN) residual corrector: engine, router, trainer
├── rust_core/            # Optional pyo3 kernels (massive_rust_core)
├── frontend/             # React 18 + Vite + TS SPA (typed DTOs generated from Python)
├── massive-ui-ng/        # Next-gen UI kit (LLM translator UX; see its README)
├── configs/llm_contract/ # Machine-readable MASSIVE↔LLM contract (v1.1.0)
├── datasets/pvu_cases/   # Offline validation cases (pre-registered)
├── benchmarks/           # PVU-BS runner + scientific benchmarks
├── docs/                 # MkDocs site + production-readiness suite
└── tests/                # 530 tests: unit, integration, contract, security, reproducibility
```

---

## 📚 Documentation

| Topic | Link |
|---|---|
| MkDocs site (API reference, validation, science) | `python -m mkdocs serve` → http://localhost:8000 |
| Architecture — current state (verified map) | [`docs/architecture/current-state.md`](docs/architecture/current-state.md) |
| Architecture — target state & open decisions | [`docs/architecture/target-state.md`](docs/architecture/target-state.md) |
| Production-readiness audit & risk matrix | [`docs/production-readiness-audit.md`](docs/production-readiness-audit.md) |
| Runbooks (dev · ops · incidents) | [`docs/runbooks/`](docs/runbooks/local-development.md) |
| Security (threat model, secrets) | [`docs/security/threat-model.md`](docs/security/threat-model.md) |
| Testing strategy & coverage | [`docs/testing/test-strategy.md`](docs/testing/test-strategy.md) |
| Performance baseline | [`docs/performance/baseline.md`](docs/performance/baseline.md) |
| Release checklist | [`docs/release-checklist.md`](docs/release-checklist.md) |
| Spanish README | [`README_ES.md`](README_ES.md) |

---

## 🤝 Contributing

PRs are welcome — see [`CONTRIBUTING.md`](CONTRIBUTING.md). In short:

```bash
make install && make test && make lint    # all three green before opening a PR
```

Engine-behavior changes require characterization tests before and numeric
tolerance comparisons after (see the testing strategy doc). New API fields must
regenerate the frontend types (`python scripts/gen_ts_types.py` — CI enforces it).

## 📜 License

Apache License 2.0 — see [`LICENSE`](LICENSE).

---

<div align="center">

*MASSIVE was previously developed as **BeyondSight** (archived in git history). Renamed 2026-06-29.*

</div>
