# MASSIVE

**Mathematical Architecture for Scalable Social Interaction & Virtual Engine**

MASSIVE is a hybrid social-dynamics platform for simulating opinion formation, polarization, intervention strategies, temporal risk and scientific diagnostics over complex social systems. It combines a stable legacy simulator with newer opt-in scientific layers for adaptive numerics, stability analysis, data assimilation, physics-inspired observables, CfC neural routing, optional Rust acceleration and validation workflows.

The guiding principle is backward compatibility: the classic APIs (`simular`, `simular_multiples`, `run_with_schedule`) remain stable, while advanced capabilities live behind explicit configuration flags and new `massive_core` modules.

---

## The ocean is not in a single water molecule

MASSIVE does not simulate individuals — it models the **emergent behavior of millions of people in interaction**. Just as the ocean is not contained in a single water molecule but in the collective, the phenomena MASSIVE captures only arise at scale.

Objecting that "humans are unpredictable" misses the point: MASSIVE models *collective* phenomena — opinion cascades, polarization, phase transitions — that have no meaning at the individual level. Meteorology does not predict individual air molecules; it maps pressure fields and temperature gradients. MASSIVE does the same for societies: it identifies **patterns and bifurcation points** that only surface when millions of decisions converge.

The theoretical foundation is the **ontology of levels**: social phenomena are irreducible to the sum of individual choices. MASSIVE is not an oracle, and it does not model consciousness. It is a tool for:

- **Exploring scenarios** before they crystallize into reality.
- **Testing interventions** in a safe, quantitative sandbox.
- **Detecting early signals** of instability and tipping points.

It sits at the intersection of complex-systems physics and quantitative social science — the same intellectual tradition that gave us thermodynamics, epidemiological models, and statistical mechanics applied to human collective behavior.

---

## Why MASSIVE is different

- **Hybrid regime reasoning:** heuristic, LLM-compatible and optional CfC neural regime selection paths coexist with safe fallbacks.
- **Scientific opt-in layer:** adaptive steppers, stability diagnostics, EnKF assimilation, bifurcation tools, statistical mechanics, network reconstruction and scientific reports are available without changing default simulation behavior.
- **Multi-engine architecture:** legacy scalar simulation, social-energy Langevin dynamics, multilayer sociodemographic dynamics and large-scale super-agent simulation are all present.
- **Optional Rust acceleration:** selected numerical kernels can use the `massive_rust_core` extension through `massive_core.rust_core`, while keeping Python fallbacks.
- **Validation-first design:** PVU-MASSIVE offline validation, canonical scientific benchmarks and a broad pytest suite support reproducibility.
- **Typed backend/frontend contract:** Pydantic DTOs generate TypeScript interfaces through `scripts/gen_ts_types.py`.

---

## 🌍 CIA World Factbook Integration

MASSIVE now supports realistic country-specific simulations using data from the CIA World Factbook. This integration enables agents to be initialized with real demographic data, social pressure to be calculated using actual ethnic and religious diversity, and economic constraints to be based on real GDP and Gini index values.

**5 Integration Points:**
1. **Agent Initialization** - Scale agent counts and demographics from real population data
2. **Social Pressure** - Use ethnic/religious/linguistic diversity for realistic group dynamics  
3. **Energy Engine** - Gini index modulates attractor/repeller strengths in social landscapes
4. **Intervention Optimizer** - Economic constraints based on real GDP and budget data
5. **Validation Framework** - Compare simulation results against Factbook metrics

**Quick Start:**
```python
from massive.core.factbook import FactbookContext

# Load country data
context = FactbookContext()
context.load_country("US")

# Get MASSIVE parameters
params = context.get_massive_params("US")
print(f"Agents: {params['n_agents']}, Gini: {params['gini_coefficient']:.3f}")
```

The repository ships sample data for the CIA country codes `US`, `CH` (China) and `GM` (Germany) in `data/factbook/factbook_sample.json`. A full dataset (260+ countries) can be loaded from [wmccaffrey/cia_world_factbook](https://github.com/wmccaffrey/cia_world_factbook). See `FACTBOOK_INTEGRATION_COMPLETE.md` for full documentation.

---

## Repository map

| Area | Files | Purpose |
| --- | --- | --- |
| Legacy simulator | `simulator.py` | Stable public API, regime rules, LLM/heuristic selection, schedule execution. |
| Scientific adapter | `massive_core/` | Stable import surface and opt-in scientific modules. |
| Numerical integration | `massive_core/numerics/` | `DynamicsStepper`, Euler-Maruyama baseline, adaptive solver, stability tools. |
| Diagnostics | `massive_core/diagnostics/`, `massive_core/benchmarks/` | `ScientificReport`, canonical fixed-point/tipping/network benchmarks. |
| Data assimilation | `massive_core/data_assimilation/` | Ensemble Kalman Filter and sparse observation assimilation workflows. |
| Physics modules | `massive_core/physics/`, `massive_core/dynamical_systems/` | Statistical mechanics, perturbation, hydrodynamics, bifurcation analysis. |
| Meta-learning/CfC | `cfc_engine.py`, `cfc_router.py`, `cfc_trainer.py`, `massive_core/metalearning/` | Closed-form continuous-time neural models and training-data adapters. |
| Rust acceleration | `rust_core/`, `massive_core/rust_core.py` | Optional compiled kernels with Python-compatible fallbacks for selected numerical routines. |
| Energy engine | `energy_engine.py`, `energy_runner.py`, `energy_schemas.py` | Social-energy landscape dynamics and programmatic landscape generation. |
| Multilayer engine | `multilayer_engine.py`, `massive_engine.py`, `massive_core/numerics/multilayer_engine_sparse.py` | Sociodemographic multilayer simulation, sparse-engine optimisation and scalable super-agent execution. |
| Forecasting | `forecast/` | Analytical and Monte Carlo temporal forecasts and scenario comparison. |
| Strategy design | `social_architect.py`, `intervention_optimizer.py`, `programmatic_architect.py` | Inverse intervention design and optimization. |
| Validation | `benchmarks/`, `datasets/pvu_cases/`, `docs/validation/` | PVU-MASSIVE cases, metrics and validation reports. |
| **CIA World Factbook** | `massive/core/factbook/`, `data/factbook/` | Country-specific demographic, economic, social data integration for realistic simulations. |
| UI/API contract | `backend/app/main.py`, `backend/app/models/`, `frontend/src/types/` | FastAPI UI-NG backend, DTOs and generated TypeScript types. |

---

## AI-ready repository bundle with Repomix

MASSIVE includes a Repomix configuration so any AI assistant can inspect the repository as a single, structured XML file without committing generated bundles.

```bash
npx --yes repomix@latest --config repomix.config.json
```

The command writes `repomix-output.xml` using `.gitignore`, `.repomixignore`, and `repomix-instruction.md` to keep local secrets, caches, build artifacts, binary assets and generated outputs out of the AI bundle. For a smaller structural snapshot, run:

```bash
npx --yes repomix@latest --config repomix.config.json --compress -o repomix-output-compressed.xml
```

## Installation

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Optional environment variables are documented in `.env.example`. For local Ollama runs, set `OLLAMA_HOST` if different from `http://localhost:11434`.

---

## Quick start

### Run the UI-NG frontend + API (single-service)

MASSIVE ships a self-contained FastAPI backend that also serves the built UI-NG
frontend (Angular + Vite) from `frontend/dist`. No separate web server is needed.

```bash
# 1. Install backend deps
pip install -r requirements.txt

# 2. Build the UI-NG frontend (once) — produces frontend/dist
cd frontend && npm ci && npm run build && cd ..

# 3. Serve everything (API on :8000, frontend mounted at /)
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000` — the UI-NG app loads and the API powers it
through the same port (`/docs` for the OpenAPI UI, `/health`, `/metrics`, SSE
endpoints). To run API-only (no frontend), start with
`MASSIVE_SERVE_FRONTEND=0 uvicorn ...`.

### Run the legacy simulator

```python
from simulator import simular, resumen_historial

estado = {
    "opinion": 0.5,
    "propaganda": 0.7,
    "confianza": 0.4,
    "opinion_grupo_a": 0.72,
    "opinion_grupo_b": 0.28,
    "pertenencia_grupo": 0.65,
}

historial = simular(estado, pasos=30, cada_n_pasos=5, verbose=False)
print(resumen_historial(historial))
```

### Run with scientific reporting

```python
from massive_core import run_scientific_simulation

result = run_scientific_simulation(
    estado,
    pasos=30,
    scientific_config={"enable_scientific_report": True},
    verbose=False,
)

print(result.scientific_report.to_dict())
```

### Assimilate observations with EnKF

```python
result = run_scientific_simulation(
    estado,
    pasos=30,
    scientific_config={"enable_data_assimilation": True},
    observations={30: 0.82},
    verbose=False,
)

print(result.assimilation_result.to_dict())
```

### Use opt-in steppers in engines

```python
from energy_engine import SocialEnergyEngine

engine = SocialEnergyEngine(
    range_type="bipolar",
    temperature=0.0,
    scientific_config={"solver": "euler_maruyama"},
)
```

The default is `solver="legacy"`, so existing behavior is preserved unless a scientific solver is explicitly selected.

### Run with CIA World Factbook data

```python
from massive.core.factbook import FactbookContext
from massive_engine import MassiveEngine
from energy_engine import SocialEnergyEngine

# Initialize with country-specific data
context = FactbookContext()
context.load_country("US")
params = context.get_massive_params("US")

# Create engine with real demographic data
engine = MassiveEngine(config={"n_agents": params["n_agents"]})

# Use Gini index in energy landscape
energy_engine = SocialEnergyEngine(
    gini_coefficient=params["gini_coefficient"],
    inequality_factor=params["inequality_factor"],
)
```

### Run canonical scientific benchmarks

```python
from massive_core import run_canonical_benchmarks

print(run_canonical_benchmarks())
```

### LLM-NL Simulation Pipeline (v1.1)

MASSIVE exposes a natural-language-to-simulation endpoint powered by the
LLM orchestrator. The orchestrator classifies intent → augments config from
the CIA World Factbook → validates → dispatches the correct engine → narrates
results. See `configs/llm_contract/massive_llm_contract.json` for the full
knowledge contract and `docs/MASSIVE_LLM_INTERFACE.md` for prompt templates.

```bash
# NL simulation (requires PROVIDER + LLM key; falls back gracefully)
curl -X POST http://localhost:8000/v1/llm/run_simulation \
  -H "X-API-Key: $MASSIVE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"intent": "alta polarización en Brasil, horizonte 90 días, confianza 95%"}'
```

Response includes `simulation_id`, `classified_motor`, `result.metrics`,
`narrative_summary`, `assumptions`, and `confidence_bounds`.

**Country detection** — the orchestrator auto-detects 95+ countries from NL text
(ISO2→CIA mapping via FactbookContext). When a country is identified, the engine
is automatically parametrized with real demographic/economic data.

---

### Sparse multilayer engine

A fully sparse implementation of the multilayer graph engine based on
``scipy.sparse`` structures for reduced memory and faster iteration on
large systems:

```python
import numpy as np

from massive_core.numerics import SparseMultilayerEngine, LayerState
from scipy import sparse

layer = LayerState(
    node_features=np.random.randn(100, 8),
    graph_adjacency=sparse.random(100, 100, density=0.05, format="csr"),
    layer_id="social",
)
engine = SparseMultilayerEngine(layers=[layer])
result = engine.run_simulation()
```

### Stability and perturbation analysis

``StabilityAnalyzer`` computes the Jacobian at equilibrium and classifies
local stability via eigenvalue analysis; ``PerturbationTheorySolver``
provides state perturbations and parameter-sensitivity diagnostics:

```python
from massive_core.numerics import StabilityAnalyzer
from massive_core.physics import PerturbationTheorySolver

analyzer = StabilityAnalyzer(system_fn, equilibrium)
report = analyzer.analyze()
print(report.is_stable)
```

### Sparse ensemble Kalman filter

``SparseEnsembleKalmanFilter`` runs EnKF analysis on a subset of observable
variables, ideal for high-dimensional social systems where only a fraction
of the state is measured:

```python
import numpy as np

from massive_core.data_assimilation import SparseEnsembleKalmanFilter

ekf = SparseEnsembleKalmanFilter(
    n_ensemble=50,
    n_state_dim=200,
    n_obs_dim=20,
    observable_indices=list(range(20)),
    observation_covariance=np.eye(20) * 0.1,
)
state_estimate, ensemble = ekf.assimilate_step(model_fn, observations)
```

---

## CfC neural reasoning support

MASSIVE includes Closed-form Continuous-time (CfC) components:

- `CfCRegimeSelector` for fast regime selection.
- `CfCTauMatrix` for sociodemographic noise modulation.
- `CfCArchitectPolicy` for intervention proposals.
- `massive_core.metalearning.cfc_training_data` to transform MASSIVE histories into tensors compatible with the CfC trainer.

Training remains optional and model files are loaded from `models/` by `CfCRouter` when available.

```python
from massive_core import build_cfc_regime_dataset_from_history

dataset = build_cfc_regime_dataset_from_history(historial, window_size=6)
```

---

## Validation and checks

```bash
# Unit/integration suite
python -m pytest tests/

# PVU-MASSIVE offline validation
python -m benchmarks.runner --cases datasets/pvu_cases --offline --out reports/validation/local --seed 42

# Regenerate frontend TypeScript contracts
python scripts/gen_ts_types.py

# Build documentation
python -m mkdocs build --strict
```

---

## Documentation

- MkDocs site: `docs/`
- API reference: `docs/api.md`
- Scientific roadmap in Spanish: `docs/math_physics_extension_plan_ES.md`
- PVU-MASSIVE validation protocol: `docs/validation/`
- Spanish overview: `README_ES.md`
- Benchmark card: docs/cards/BENCHMARK.md
- Reproducibility card: docs/cards/REPRODUCIBILITY.md
- Real-engine benchmark report: `experiments/06_real_benchmark_v0/REPORT.md`
- Historical empirical validation report: `experiments/real_validation/EMPIRICAL_VALIDATION_REPORT.md`

---

## 🚀 Production Readiness (v1.1)

### Endpoints Versioned (`/v1/*`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/v1/simulate` | POST | Simulación básica (scalar, energy, multilayer, massive) |
| `/v1/scientific` | POST | Simulación con reporte científico (assimilación, estabilidad) |
| `/v1/factbook` | GET | Parámetros de país / validación |
| `/v1/benchmarks` | POST | Benchmarks canónicos (PVU-BS) |
| `/v1/forecast` | POST | Previsión temporal + intervenciones |
| `/v1/llm/run_simulation` | POST | NL → simulación completa (ver contrato en `configs/llm_contract/`) |
| `/health` | GET | Liveness/readiness probe (Docker HEALTHCHECK) |
| `/metrics` | GET | Prometheus text-format counters |

### Docker (single-service)

```bash
# Build + run (API + UI en :8000)
docker compose -f infra/docker-compose.yml up --build

# Health check
curl http://localhost:8000/health
```

Multi-stage Dockerfile: Node 20 builder → Python 3.11-slim runtime. Frontend
mountado en `frontend/dist/`, servido por FastAPI estático.

### CI/CD Pipeline

```
Push / Pull Request → branch: main
  1. lint        — ruff check + mypy --strict
  2. test        — pytest --cov (453 tests, 0 failures)
  3. docs        — mkdocs build --strict
  4. frontend    — npm ci && npm run build
  5. benchmark   — pyytest benchmarks/runner.py (solo en release tag)
  └── 6. publish — PyPI + Docker Hub (solo en release tags: push v*)
```

### Variables de Entorno Clave (`.env.example`)

```bash
MASSIVE_ENV=production
MASSIVE_API_KEYS=change-me-prod-key-1,change-me-prod-key-2
MASSIVE_CORS_ORIGINS=https://app.massive.io
MASSIVE_SERVE_FRONTEND=1
MASSIVE_DATA_DIR=/data
PROVIDER=groq|openai|openrouter|none  # proveedor LLM
MASSIVE_LLM_MODEL=llama-3.1-70b       # modelo (si PROVIDER configurado)
```

### Observabilidad y Seguridad

- **SLOs definidos:** latencia p95 (<2s simulaciones), tasa de error (<0.1%), disponibilidad mensual (99.9%)
- **Logging:** JSON estructurado con `request_id`, `simulation_id`, `engine_type`, `country_code`, `llm_provider`, `user_id` (configurar con `MASSIVE_LOG_FORMAT=json`)
- **Rate limiting:** sliding-window por IP; límites configurables vía `MASSIVE_RATE_LIMIT_*`
- **Security headers:** CSP, X-Frame-Options=DENY, nosniff, Permissions-Policy
- **Auditoría:** eventos de configuración registrados (ver `docs/OBSERVABILITY_AND_SECURITY.md`)

### Testing

```bash
# Suite completa (453 tests)
pytest tests/ -v --cov=massive --cov=backend --cov-report=term-missing

# Solo endpoint LLM
pytest tests/test_llm_endpoint.py -v

# PVU-BS validation
python -m benchmarks.runner --cases datasets/pvu_cases --out reports/validation/
```

**Cobertura actual:** 47% (objetivo 80% en próximos sprints). Módulos LLM al 94.5%.

---

## Deployment notes

- CI deploy no longer uses force-push to Hugging Face Spaces.
- Configure `HF_TOKEN` in repository secrets for Hugging Face sync.
- Optional analytics in the UI-NG app can be injected with `MASSIVE_ANALYTICS_SNIPPET`; no placeholder script is emitted by default.
- Docker (`infra/docker-compose.yml`) runs the FastAPI backend on port `8000` and
  mounts the pre-built `frontend/dist` so the UI-NG app is served from the same
  container. No Streamlit process or extra web server is required.
- To disable self-serving of the frontend in a container, set
  `MASSIVE_SERVE_FRONTEND=0`; the backend stays API-only on `:8000`.

---

## License

Apache License 2.0. See `LICENSE`.
