# MASSIVE

**Mathematical Architecture for Scalable Social Interaction & Virtual Engine**

> A hybrid social-dynamics simulation platform that predicts opinion formation, polarization, and intervention outcomes over complex social systems — with optional Rust acceleration, real-world Factbook data, and scientifically validated numerics.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](pyproject.toml)
[![Version: 0.1.0](https://img.shields.io/badge/version-0.1.0-blue)](pyproject.toml)
[![Build: Passing](https://github.com/Adlgr87/MASSIVE/actions/workflows/pytest.yml/badge.svg?branch=main)](.github/workflows/pytest.yml)
[![Rust: Optional](https://img.shields.io/badge/Rust-optional-orange?logo=rust)](Cargo.toml)
[![Type-check: MyPy](https://github.com/Adlgr87/MASSIVE/actions/workflows/typecheck.yml/badge.svg)](.github/workflows/typecheck.yml)

![Demo](docs/demo.gif)

---

## ✨ Features

- **Opinion & polarization simulation** — backward-compatible legacy API (`simular`, `run_with_schedule`) plus energy-based Langevin dynamics.
- **Real-world data integration** — initialize agents with CIA World Factbook demographics for 260+ countries.
- **Rust acceleration** — optional compiled numerical kernels (`massive_rust_core`) with Python fallbacks.
- **Scientific opt-in layer** — adaptive steppers, stability analysis, EnKF assimilation, bifurcation diagnostics.
- **API-first design** — FastAPI backend with auth-gated endpoints (`/api/v1/forecast`, `/api/v1/architect`, `/api/v1/energy`).

---

## 🛠️ Tech Stack

| Category | Technology | Why |
|---|---|---|
| **Core** | Python 3.11, numpy, scipy, networkx, pydantic | Numerical + graph + typed contract |
| **Acceleration** | Rust (`maturin`, `pyo3`) | Hot-path numerical kernels |
| **API** | FastAPI, uvicorn | Low-latency, auto-documented HTTP API |
| **Scientific** | numba, statsmodels, pgmpy, nashpy, dask | Optional engines behind config flags |
| **Frontend** | React 18, Vite, TypeScript, Tailwind | Modern SPA with auto-generated DTOs |
| **ML/AI** | OpenAI, LangChain, PyTorch (Mamba, CfC) | LLM-based architect + SNN baselines |
| **Deployment** | Docker multi-stage, nginx, supervisord | Single gateway, non-root runtime |

---

## 🚀 Quick Start (60 seconds)

```bash
git clone https://github.com/Adlgr87/MASSIVE.git
cd MASSIVE
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env    # add your API key if needed
python app.py           # opens Streamlit UI
```

**No Streamlit?** Run the API server instead:
```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

> **Minimum requirement:** Python 3.11, 500 MB free RAM. Rust/CUDA/torch are optional.

---

## 🧪 Run a Simulation (30 seconds)

```python
from simulator import simular, resumen_historial

estado = {
    "opinion": 0.5, "propaganda": 0.7, "confianza": 0.4,
    "opinion_grupo_a": 0.72, "opinion_grupo_b": 0.28,
    "pertenencia_grupo": 0.65,
}
historial = simular(estado, pasos=30, cada_n_pasos=5)
print(resumen_historial(historial))
```

---

## 🐳 Docker (One Command)

```bash
cp .env.example .env
docker compose up --build
# → frontend: http://localhost
# → API docs: http://localhost/api (FastAPI /docs)
```

---

## 📊 Scientific Backends

```python
from massive_core import run_scientific_simulation
result = run_scientific_simulation(
    estado, pasos=30,
    scientific_config={"enable_scientific_report": True},
)
print(result.scientific_report.to_dict())
```

| Engine | Purpose | Activate via |
|---|---|---|
| `social_architect` | Inverse intervention strategy | `from social_architect import buscar_estrategia_inversa` |
| `forecast/engine.py` | Temporal risk forecast | `/api/v1/forecast` |
| `energy_runner` | Social-energy landscape | `/api/v1/energy`, `SocialEnergyEngine(solver="euler_maruyama")` |
| `SparseMultilayerEngine` | Scalable super-agent sim | `from massive_core.numerics import SparseMultilayerEngine` |
| `SparseEnsembleKalmanFilter` | Data assimilation | `from massive_core.data_assimilation import SparseEnsembleKalmanFilter` |

---

## 📡 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/architect` | POST | Inverse-strategy search to reach a user goal |
| `/api/v1/forecast` | POST | Analytical + Monte Carlo temporal forecast |
| `/api/v1/energy` | POST | Social-energy landscape simulation |
| `/api/extract` | POST | File → MASSIVE config (PDF/JSON/CSV) |
| `/api/wizard` | POST | LLM-powered simulation wizard |
| `/health` | GET | Liveness probe |
| `/ready` | GET | Readiness probe |
| `/docs` | GET | OpenAPI UI (FastAPI) |

**Auth:** `X-API-Key` header or `MASSIVE_API_KEY` env var. Dev fallback: `dev-secret-key`.

---

## 🔬 Development & Testing

```bash
# Install dev extras
pip install -e ".[dev,api,ml,scientific]"

# Test suite
python -m pytest tests/ -x -q

# PVU-MASSIVE offline validation
python -m benchmarks.runner --cases datasets/pvu_cases --offline --out reports/validation/local --seed 42

# Type checking
python scripts/typecheck_slice.py

# Regenerate frontend types
python scripts/gen_ts_types.py

# Build Rust core (optional)
maturin develop --release
```

---

## 📚 Documentation

| Topic | Link |
|---|---|
| Full API reference | [`docs/api.md`](docs/api.md) |
| Scientific roadmap (ES) | [`docs/math_physics_extension_plan_ES.md`](docs/math_physics_extension_plan_ES.md) |
| PVU-MASSIVE validation | [`docs/validation/`](docs/validation/) |
| CIA Factbook integration | [`docs/FACTBOOK_INTEGRATION_COMPLETE.md`](docs/FACTBOOK_INTEGRATION_COMPLETE.md) |
| MkDocs site | `python -m mkdocs serve` |
| Spanish README | [`README_ES.md`](README_ES.md) |

---

## 📜 License

Apache License 2.0. See [`LICENSE`](LICENSE).

---

> MASSIVE was previously developed as **BeyondSight** (archived in git history). Codebase renamed 2026-06-29.
